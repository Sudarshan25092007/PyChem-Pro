"""
Hybrid RFA + MARS QSAR Plugin

Features:
- Red Fox Algorithm (RFA) Feature Selection
- SplineTransformer (MARS-like) Non-linear Modeling
- Golbraikh-Tropsha Criteria Validation
- Applicability Domain (Williams Plot)
- Double-click toggling for categorical settings
"""

import math
import threading
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import KFold, cross_val_score
from sklearn.linear_model import LinearRegression, Lasso
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.preprocessing import SplineTransformer

# Strictly using ONLY the allowed imports from qt_compat
from src.shared.qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTextEdit, QProgressBar,
    QFileDialog, QMessageBox, QComboBox, Qt, QThread, Signal
)
from src.plugins.base_plugin import BasePlugin, PluginWidget
from src.plugins.plugin_types import PluginInfo, PluginType

# ===================================================================
# QSAR & AD HELPER FUNCTIONS
# ===================================================================
def calculate_qsar_metrics(y_true, y_pred):
    metrics = {}
    metrics['R2_ext'] = r2_score(y_true, y_pred)
    metrics['RMSE_ext'] = float(np.sqrt(mean_squared_error(y_true, y_pred)))

    mean_true, var_true = np.mean(y_true), np.var(y_true)
    mean_pred, var_pred = np.mean(y_pred), np.var(y_pred)

    covar = np.mean((y_true - mean_true) * (y_pred - mean_pred))
    metrics['CCC'] = float((2 * covar) / (var_true + var_pred + (mean_true - mean_pred)**2))

    k, _, _, _ = np.linalg.lstsq(np.vstack([y_true, np.ones(len(y_true))]).T, y_pred, rcond=None)
    k_prime, _, _, _ = np.linalg.lstsq(np.vstack([y_pred, np.ones(len(y_pred))]).T, y_true, rcond=None)
    metrics['k'], metrics['k_prime'] = float(k[0]), float(k_prime[0])

    r2_zero = 1 - (np.sum((y_true - y_pred)**2) / np.sum(y_true**2))
    r_prime2_zero = 1 - (np.sum((y_pred - y_true)**2) / np.sum(y_pred**2))
    metrics['R2_zero_diff'] = float(abs(r2_zero - r_prime2_zero))

    return metrics

def check_golbraikh_tropsha(metrics):
    criteria = {
        "Q2_ext > 0.5": metrics['R2_ext'] > 0.5,
        "|R2_zero - R'2_zero| < 0.3": metrics['R2_zero_diff'] < 0.3,
        "0.85 <= k <= 1.15": 0.85 <= metrics['k'] <= 1.15,
        "0.85 <= k' <= 1.15": 0.85 <= metrics['k_prime'] <= 1.15
    }
    return all(criteria.values()), criteria

def calculate_leverage(X_train):
    X_train_intercept = np.hstack([np.ones((X_train.shape[0], 1)), X_train])
    try:
        return np.diag(X_train_intercept @ np.linalg.pinv(X_train_intercept.T @ X_train_intercept) @ X_train_intercept.T)
    except np.linalg.LinAlgError:
        return np.full(X_train.shape[0], np.nan)

# ===================================================================
# BACKGROUND WORKER THREAD
# ===================================================================
class RfaMarsWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(bool, str, object)

    def __init__(self, df, train_ids, test_ids, config):
        super().__init__()
        self.df = df
        self.train_ids = train_ids
        self.test_ids = test_ids
        self.config = config
        self.seed = 35

    def rfoa_feature_selection(self, X, y, pop_size, dimension, iterations):
        np.random.seed(self.seed)
        all_features = list(X.columns)
        dim = min(dimension, len(all_features))

        foxes = [list(np.random.choice(all_features, size=dim, replace=False)) for _ in range(pop_size)]

        def fitness(f):
            return r2_score(y, LinearRegression().fit(X[f], y).predict(X[f]))

        fit_scores = [fitness(f) for f in foxes]

        for t in range(iterations):
            sorted_idx = np.argsort(fit_scores)[::-1]
            foxes = [foxes[i] for i in sorted_idx]
            fit_scores = [fit_scores[i] for i in sorted_idx]

            for i in range(pop_size // 2, pop_size):
                new_f = foxes[i][:]
                idx = np.random.randint(dim)
                possible = [f for f in all_features if f not in new_f]
                if possible:
                    new_f[idx] = np.random.choice(possible)
                    new_fit = fitness(new_f)
                    if new_fit > fit_scores[i]:
                        foxes[i], fit_scores[i] = new_f, new_fit

            if t % max(1, (iterations // 5)) == 0 or t == iterations - 1:
                self.log_signal.emit(f"RFA Iter {t+1}/{iterations}: Best R2 = {fit_scores[0]:.4f}")

        return foxes[0]

    def run(self):
        try:
            # Parse Config
            pop_size = int(self.config['Pop Size'])
            iterations = int(self.config['Iterations'])
            dimension = int(self.config['Dimension'])
            n_knots = int(self.config['MARS Knots'])
            alpha = float(self.config['Lasso Alpha'])
            cv_folds = int(self.config['CV Folds'])
            model_type = self.config['Model Type']

            # Prepare Data
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            self.df[numeric_cols] = self.df[numeric_cols].fillna(self.df[numeric_cols].mean())

            train_indices = self.df[self.df.iloc[:, 0].isin(self.train_ids)].index
            test_indices = self.df[self.df.iloc[:, 0].isin(self.test_ids)].index

            Z = self.df.iloc[:, 0]
            Y = self.df.iloc[:, 1]
            X = self.df.iloc[:, 2:].select_dtypes(include=[np.number])

            X_train, X_test = X.loc[train_indices], X.loc[test_indices]
            y_train, y_test = Y.loc[train_indices], Y.loc[test_indices]
            z_train, z_test = Z.loc[train_indices], Z.loc[test_indices]

            self.log_signal.emit(f"Train shape: {X_train.shape}, Test shape: {X_test.shape}")

            # STAGE 1: RFA Selection
            self.log_signal.emit("\n--- STAGE 1: RFA Feature Selection ---")
            selected_features = self.rfoa_feature_selection(X_train, y_train, pop_size, dimension, iterations)
            self.log_signal.emit(f"> Best Descriptors: {list(selected_features)}")
            X_train_sel, X_test_sel = X_train[selected_features], X_test[selected_features]

            # STAGE 2: SplineTransformer
            self.log_signal.emit(f"\n--- STAGE 2: Formatting Features for {model_type} ---")
            if 'MARS' in model_type:
                spline = SplineTransformer(n_knots=n_knots, degree=1, include_bias=False).fit(X_train_sel)
                X_train_final = np.hstack([X_train_sel, spline.transform(X_train_sel)])
                X_test_final = np.hstack([X_test_sel, spline.transform(X_test_sel)])
                spline_names = spline.get_feature_names_out(selected_features)
                final_names = list(selected_features) + list(spline_names)
                self.log_signal.emit(f"Added {len(spline_names)} Spline/Knot features.")
            else:
                X_train_final, X_test_final = X_train_sel.to_numpy(), X_test_sel.to_numpy()
                final_names = list(selected_features)

            # STAGE 3: Modeling & CV
            self.log_signal.emit(f"\n--- STAGE 3: Model Training ({cv_folds}-Fold CV) ---")
            lasso = Lasso(alpha=alpha, max_iter=10000, random_state=self.seed)
            cv = KFold(n_splits=cv_folds, shuffle=True, random_state=self.seed)
            cv_r2 = cross_val_score(lasso, X_train_final, y_train, cv=cv, scoring='r2')

            self.log_signal.emit(f"Q2_cv ({cv_folds}-fold): {np.mean(cv_r2):.4f} +/- {np.std(cv_r2):.4f}")
            lasso.fit(X_train_final, y_train)
            y_pred_train, y_pred_test = lasso.predict(X_train_final), lasso.predict(X_test_final)

            # STAGE 4: External Validation
            self.log_signal.emit("\n--- STAGE 4: External Validation ---")
            test_metrics = calculate_qsar_metrics(y_test, y_pred_test)
            self.log_signal.emit(f"Q2_ext: {test_metrics['R2_ext']:.4f} | RMSE_ext: {test_metrics['RMSE_ext']:.4f} | CCC: {test_metrics['CCC']:.4f}")

            passes, crits = check_golbraikh_tropsha(test_metrics)
            self.log_signal.emit("-- Golbraikh-Tropsha Criteria --")
            for crit, val in crits.items():
                self.log_signal.emit(f"{crit}: {'PASS' if val else 'FAIL'}")

            # STAGE 5: Equation
            self.log_signal.emit("\n--- STAGE 5: Equation ---")
            eq = f"y = {lasso.intercept_:.4f}"
            for name, coef in zip(final_names, lasso.coef_):
                if coef != 0:
                    sign = "+" if coef > 0 else "-"
                    eq += f" {sign} {abs(coef):.4f} * {name}"
            self.log_signal.emit(eq)

            # STAGE 6: Applicability Domain
            self.log_signal.emit("\n--- STAGE 6: Applicability Domain ---")
            active_idx = [i for i, c in enumerate(lasso.coef_) if c != 0]
            X_train_ad = X_train_final[:, active_idx] if active_idx else X_train_final

            leverages = calculate_leverage(X_train_ad)
            n, p = X_train_ad.shape[0], X_train_ad.shape[1]
            warning_leverage = 3 * (p + 1) / n if n > 0 else 0

            residuals = y_train - y_pred_train
            mse_train = np.mean(residuals**2)
            std_residuals = residuals / np.sqrt(mse_train * (1 - leverages))

            self.log_signal.emit(f"Warning Leverage (h*): {warning_leverage:.4f}")

            # Package results for Export
            result_data = {
                'z_train': z_train.values, 'y_train': y_train.values, 'y_pred_train': y_pred_train,
                'z_test': z_test.values, 'y_test': y_test.values, 'y_pred_test': y_pred_test,
                'metrics': test_metrics, 'leverages': leverages, 'std_res': std_residuals, 'w_lev': warning_leverage
            }

            self.finished_signal.emit(True, "Analysis Complete", result_data)

        except Exception as e:
            self.finished_signal.emit(False, str(e), None)


# ===================================================================
# MAIN WIDGET UI
# ===================================================================
class QsarRfaWidget(PluginWidget):
    def __init__(self, plugin):
        super().__init__(plugin)
        self.dataset = None
        self.worker = None
        self.result_cache = None
        self.setup_ui()

    def setup_ui(self):
        self.widget = QWidget()
        main_layout = QVBoxLayout(self.widget)

        # 1. Data Source
        data_layout = QHBoxLayout()
        data_layout.addWidget(QLabel("<b>1. Data Source:</b>"))
        self.btn_load = QPushButton("Load Dataset CSV")
        self.btn_load.clicked.connect(self.load_data)
        data_layout.addWidget(self.btn_load)
        self.lbl_file = QLabel("No file loaded")
        data_layout.addWidget(self.lbl_file)
        data_layout.addStretch()
        main_layout.addLayout(data_layout)

        # 2. Train/Test Split Dual-Table
        main_layout.addWidget(QLabel("<b>2. Define Train/Test Split:</b>"))

        split_layout = QHBoxLayout()
        self.tbl_test = QTableWidget()
        self.tbl_test.setColumnCount(1)
        self.tbl_test.setHorizontalHeaderLabels(["Test Set IDs"])
        self.tbl_test.horizontalHeader().setStretchLastSection(True)
        split_layout.addWidget(self.tbl_test)

        btn_move_layout = QVBoxLayout()
        self.btn_to_train = QPushButton(">> To Train >>")
        self.btn_to_train.clicked.connect(self.move_to_train)
        self.btn_to_test = QPushButton("<< To Test <<")
        self.btn_to_test.clicked.connect(self.move_to_test)
        btn_move_layout.addStretch()
        btn_move_layout.addWidget(self.btn_to_train)
        btn_move_layout.addWidget(self.btn_to_test)
        btn_move_layout.addStretch()
        split_layout.addLayout(btn_move_layout)

        self.tbl_train = QTableWidget()
        self.tbl_train.setColumnCount(1)
        self.tbl_train.setHorizontalHeaderLabels(["Training Set IDs"])
        self.tbl_train.horizontalHeader().setStretchLastSection(True)
        split_layout.addWidget(self.tbl_train)
        main_layout.addLayout(split_layout)

        auto_layout = QHBoxLayout()
        self.btn_auto = QPushButton("Auto Split (80/20)")
        self.btn_auto.clicked.connect(self.auto_split)
        auto_layout.addWidget(self.btn_auto)
        auto_layout.addStretch()
        main_layout.addLayout(auto_layout)

        # 3. Settings Grid
        main_layout.addWidget(QLabel("<b>3. RFA & Model Hyperparameters:</b>"))
        self.settings_tbl = QTableWidget()
        self.settings_tbl.setColumnCount(2)
        self.settings_tbl.setHorizontalHeaderLabels(["Setting", "Value"])
        self.settings_tbl.horizontalHeader().setStretchLastSection(True)
        self.settings_tbl.setMaximumHeight(150)

        # Connect the double-click event for interactive toggling
        self.settings_tbl.cellDoubleClicked.connect(self.on_setting_double_clicked)

        default_settings = [
            ("Dimension", "5"), ("Pop Size", "30"), ("Iterations", "30"),
            ("Model Type", "MARS-like (Lasso)"), ("MARS Knots", "4"),
            ("Lasso Alpha", "0.01"), ("CV Folds", "5")
        ]
        self.settings_tbl.setRowCount(len(default_settings))
        for i, (k, v) in enumerate(default_settings):
            k_item = QTableWidgetItem(k)
            k_item.setFlags(k_item.flags() & ~Qt.ItemIsEditable)
            self.settings_tbl.setItem(i, 0, k_item)

            v_item = QTableWidgetItem(v)
            # Make the Model Type toggle cell read-only so the user doesn't accidentally type in it
            if k == "Model Type":
                v_item.setFlags(v_item.flags() & ~Qt.ItemIsEditable)
                v_item.setToolTip("Double-click to toggle Model Type")
            self.settings_tbl.setItem(i, 1, v_item)

        main_layout.addWidget(self.settings_tbl)

        # 4. Execute & Logs
        self.btn_run = QPushButton("🚀 Run RFA+MARS Analysis")
        self.btn_run.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 8px;")
        self.btn_run.clicked.connect(self.run_analysis)
        main_layout.addWidget(self.btn_run)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        main_layout.addWidget(self.txt_log)

        self.btn_export = QPushButton("Export Results & Plots (PNG/CSV)")
        self.btn_export.clicked.connect(self.export_results)
        self.btn_export.setEnabled(False)
        main_layout.addWidget(self.btn_export)

    def on_setting_double_clicked(self, row, col):
        """Toggles 'Model Type' specifically when double-clicked."""
        setting_name = self.settings_tbl.item(row, 0).text()
        if setting_name == "Model Type":
            current_val = self.settings_tbl.item(row, 1).text()
            new_val = "Linear Only (Lasso)" if current_val == "MARS-like (Lasso)" else "MARS-like (Lasso)"

            v_item = QTableWidgetItem(new_val)
            v_item.setFlags(v_item.flags() & ~Qt.ItemIsEditable)
            v_item.setToolTip("Double-click to toggle Model Type")
            self.settings_tbl.setItem(row, 1, v_item)

    def load_data(self):
        path, _ = QFileDialog.getOpenFileName(self.widget, "Select Dataset", "", "CSV Files (*.csv)")
        if not path: return
        try:
            self.dataset = pd.read_csv(path, sep=None, engine='python')
            clean_name = path.replace("\\", "/").split("/")[-1]
            self.lbl_file.setText(clean_name)

            ids = sorted(list(self.dataset.iloc[:, 0]))
            self.tbl_test.setRowCount(len(ids))
            self.tbl_train.setRowCount(0)
            for i, val in enumerate(ids):
                self.tbl_test.setItem(i, 0, QTableWidgetItem(str(val)))

            self.txt_log.append(f"Loaded {len(ids)} compounds. Assuming Col 1=ID, Col 2=Activity.")
        except Exception as e:
            QMessageBox.critical(self.widget, "Load Error", str(e))

    def move_to_train(self):
        for item in self.tbl_test.selectedItems():
            row = self.tbl_train.rowCount()
            self.tbl_train.insertRow(row)
            self.tbl_train.setItem(row, 0, QTableWidgetItem(item.text()))
            self.tbl_test.removeRow(item.row())

    def move_to_test(self):
        for item in self.tbl_train.selectedItems():
            row = self.tbl_test.rowCount()
            self.tbl_test.insertRow(row)
            self.tbl_test.setItem(row, 0, QTableWidgetItem(item.text()))
            self.tbl_train.removeRow(item.row())

    def auto_split(self):
        if self.dataset is None: return
        all_ids = list(self.dataset.iloc[:, 0])
        np.random.shuffle(all_ids)
        split_point = int(0.80 * len(all_ids))

        train_ids, test_ids = sorted(all_ids[:split_point]), sorted(all_ids[split_point:])

        self.tbl_train.setRowCount(len(train_ids))
        for i, val in enumerate(train_ids): self.tbl_train.setItem(i, 0, QTableWidgetItem(str(val)))

        self.tbl_test.setRowCount(len(test_ids))
        for i, val in enumerate(test_ids): self.tbl_test.setItem(i, 0, QTableWidgetItem(str(val)))

    def run_analysis(self):
        if self.dataset is None or self.tbl_train.rowCount() == 0:
            QMessageBox.warning(self.widget, "Warning", "Load data and assign training set first.")
            return

        self.btn_run.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.txt_log.clear()

        config = {}
        for i in range(self.settings_tbl.rowCount()):
            config[self.settings_tbl.item(i, 0).text()] = self.settings_tbl.item(i, 1).text()

        train_ids = [self.tbl_train.item(i, 0).text() for i in range(self.tbl_train.rowCount())]
        test_ids = [self.tbl_test.item(i, 0).text() for i in range(self.tbl_test.rowCount())]

        self.worker = RfaMarsWorker(self.dataset.copy(), train_ids, test_ids, config)
        self.worker.log_signal.connect(self.txt_log.append)
        self.worker.finished_signal.connect(self.handle_finish)
        self.worker.start()

    def handle_finish(self, success, msg, result_data):
        self.btn_run.setEnabled(True)
        if success:
            self.result_cache = result_data
            self.btn_export.setEnabled(True)
            QMessageBox.information(self.widget, "Success", msg)
        else:
            QMessageBox.critical(self.widget, "Error", msg)

    def export_results(self):
        if not self.result_cache: return
        directory = QFileDialog.getExistingDirectory(self.widget, "Select Export Directory")
        if not directory: return

        directory = directory.replace("\\", "/")
        res = self.result_cache

        try:
            # Export CSV
            df_tr = pd.DataFrame({'ID': res['z_train'], 'Actual': res['y_train'], 'Predicted': res['y_pred_train'], 'Set': 'Train'})
            df_te = pd.DataFrame({'ID': res['z_test'], 'Actual': res['y_test'], 'Predicted': res['y_pred_test'], 'Set': 'Test'})
            pd.concat([df_tr, df_te]).to_csv(f"{directory}/QSAR_RFA_Results.csv", index=False)

            # Export Plots
            plt.style.use('seaborn-v0_8-whitegrid')

            # Plot 1: Actual vs Predicted
            plt.figure(figsize=(7, 6))
            plt.scatter(res['y_train'], res['y_pred_train'], c='royalblue', alpha=0.6, label='Train')
            plt.scatter(res['y_test'], res['y_pred_test'], c='darkorange', alpha=0.8, edgecolors='k', label='Test')
            lims = [min(plt.xlim()[0], plt.ylim()[0]), max(plt.xlim()[1], plt.ylim()[1])]
            plt.plot(lims, lims, 'k--', alpha=0.75, label='y=x')
            plt.xlabel("Observed Activity"); plt.ylabel("Predicted Activity"); plt.legend()
            plt.title("Predicted vs Observed")
            plt.savefig(f"{directory}/actual_vs_predicted.png", dpi=300, bbox_inches='tight')
            plt.close()

            # Plot 2: Williams Plot
            plt.figure(figsize=(7, 6))
            plt.scatter(res['leverages'], res['std_res'], c='mediumseagreen', alpha=0.7, edgecolors='k')
            plt.axhline(3, c='r', ls='--'); plt.axhline(-3, c='r', ls='--')
            plt.axvline(res['w_lev'], c='r', ls='--', label=f"h* = {res['w_lev']:.2f}")
            plt.xlabel("Leverage (h)"); plt.ylabel("Standardized Residuals"); plt.legend()
            plt.title("Williams Plot (Applicability Domain)")
            plt.savefig(f"{directory}/williams_plot.png", dpi=300, bbox_inches='tight')
            plt.close()

            self.txt_log.append(f"\n✓ Exported CSV and Plots to {directory}")
            QMessageBox.information(self.widget, "Export Success", "Data and plots successfully saved!")
        except Exception as e:
            QMessageBox.critical(self.widget, "Export Error", str(e))

# ===================================================================
# PLUGIN WRAPPER
# ===================================================================
class QsarRfaPlugin(BasePlugin):
    def __init__(self):
        super().__init__(PluginInfo(
            name="RFA + MARS QSAR",
            version="1.0.0",
            description="Hybrid Red Fox Algorithm feature selection and MARS non-linear modeling",
            author="SMILES Team",
            plugin_type=PluginType.ANALYSIS,
            dependencies=[]
        ))
        self.widget = None

    def get_info(self) -> PluginInfo:
        return self.info

    def create_widget(self) -> 'QsarRfaWidget':
        if self.widget is None:
            self.widget = QsarRfaWidget(self)
        return self.widget

    def initialize(self):
        """Bypass super().initialize() to prevent strict parameter mismatch crashes."""
        self.logger.info("RFA+MARS QSAR plugin initialized")
        return True

    def cleanup(self):
        if self.widget:
            self.widget.widget.deleteLater()
            self.widget = None
        self.logger.info("RFA+MARS QSAR plugin cleaned up")