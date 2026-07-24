import os
import json
import random
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from cutoffs.models import Cutoff
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


class Command(BaseCommand):
    help = 'Train all ML models: XGBoost'

    def add_arguments(self, parser):
        parser.add_argument(
            '--models',
            nargs='+',
            default=['xgboost'],
            help='Specify which models to train. Options: xgboost'
        )

    def handle(self, *args, **options):
        selected_models = options['models']
        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write(self.style.NOTICE("  NextCollege AI - Multi-Model Training Pipeline"))
        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write(f"Models to train: {', '.join(selected_models)}\n")

        # ── Step 1: Fetch Data ──────────────────────────────────────
        self.stdout.write("Step 1/1: Fetching historical cutoffs from database...")
        cutoffs = Cutoff.objects.filter(closing_rank__gt=0).values(
            'college_id', 'branch_id', 'category', 'seat_pool', 'closing_rank'
        )

        if not cutoffs.exists():
            self.stdout.write(self.style.ERROR("No cutoff data found. Cannot train models."))
            return

        df = pd.DataFrame(list(cutoffs))
        self.stdout.write(self.style.SUCCESS(f"  > Loaded {len(df):,} cutoff records."))

        # ── Step 2: Encode Features ────────────────────────────────
        self.stdout.write("\nStep 2/4: Encoding categorical features...")
        le_category = LabelEncoder()
        le_seat_pool = LabelEncoder()

        df['category_encoded'] = le_category.fit_transform(df['category'])
        df['seat_pool_encoded'] = le_seat_pool.fit_transform(df['seat_pool'])

        os.makedirs(os.path.join(settings.BASE_DIR, 'ml_models'), exist_ok=True)
        joblib.dump(le_category, os.path.join(settings.BASE_DIR, 'ml_models', 'le_category.pkl'))
        joblib.dump(le_seat_pool, os.path.join(settings.BASE_DIR, 'ml_models', 'le_seat_pool.pkl'))
        self.stdout.write(self.style.SUCCESS(f"  > Encoded {len(le_category.classes_)} categories, {len(le_seat_pool.classes_)} seat pools."))

        # ── Step 3: Generate Synthetic Training Data ───────────────
        self.stdout.write("\nStep 3/4: Generating synthetic training data...")
        synthetic_data = []
        for row in df.itertuples():
            c_rank = row.closing_rank

            # Positive samples (admitted - rank <= closing rank)
            for _ in range(2):
                student_rank = random.randint(max(1, int(c_rank * 0.5)), c_rank)
                synthetic_data.append([
                    row.college_id, row.branch_id, row.category_encoded,
                    row.seat_pool_encoded, student_rank, 1
                ])

            # Negative samples (not admitted - rank > closing rank)
            for _ in range(2):
                student_rank = random.randint(c_rank + 1, int(c_rank * 1.5) + 1000)
                synthetic_data.append([
                    row.college_id, row.branch_id, row.category_encoded,
                    row.seat_pool_encoded, student_rank, 0
                ])

        train_df = pd.DataFrame(synthetic_data, columns=[
            'college_id', 'branch_id', 'category_encoded', 'seat_pool_encoded', 'student_rank', 'admitted'
        ])

        X = train_df.drop('admitted', axis=1)
        y = train_df['admitted']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.stdout.write(self.style.SUCCESS(f"  > Generated {len(train_df):,} training samples."))
        self.stdout.write(f"  > Train: {len(X_train):,} | Test: {len(X_test):,}\n")

        # ── Step 4: Train Each Model ───────────────────────────────
        self.stdout.write("Step 4/4: Training models...\n")
        feature_names = list(X.columns)
        model_report = {}

        # ─── XGBoost ───
        if 'xgboost' in selected_models:
            self.stdout.write("  [+] Training XGBoost Classifier...")
            try:
                import xgboost as xgb
                xgb_model = xgb.XGBClassifier(
                    objective='binary:logistic',
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=6,
                    random_state=42,
                    n_jobs=-1,
                    eval_metric='logloss'
                )
                xgb_model.fit(X_train, y_train)
                y_pred = xgb_model.predict(X_test)
                acc = accuracy_score(y_test, y_pred)
                cm = confusion_matrix(y_test, y_pred).tolist()
                report = classification_report(y_test, y_pred, output_dict=True)

                # Feature importances
                importances = dict(zip(feature_names, [float(v) for v in xgb_model.feature_importances_]))

                model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'xgboost_admission_model.pkl')
                joblib.dump(xgb_model, model_path)

                model_report['xgboost'] = {
                    'name': 'XGBoost Classifier',
                    'type': 'Ensemble (Gradient Boosting)',
                    'accuracy': round(acc, 4),
                    'precision': round(report['weighted avg']['precision'], 4),
                    'recall': round(report['weighted avg']['recall'], 4),
                    'f1_score': round(report['weighted avg']['f1-score'], 4),
                    'confusion_matrix': cm,
                    'feature_importances': importances,
                    'hyperparameters': {
                        'n_estimators': 100,
                        'learning_rate': 0.1,
                        'max_depth': 6,
                        'objective': 'binary:logistic',
                    },
                    'training_samples': len(X_train),
                    'test_samples': len(X_test),
                    'trained_at': datetime.now().isoformat(),
                    'model_file': 'xgboost_admission_model.pkl',
                }
                self.stdout.write(self.style.SUCCESS(f"     OK XGBoost - Accuracy: {acc:.4f}"))
            except ImportError:
                self.stdout.write(self.style.WARNING("     WARN xgboost not installed, skipping."))

        # ─── Decision Tree ───
        if 'decision_tree' in selected_models:
            self.stdout.write("  [+] Training Decision Tree Classifier...")
            from sklearn.tree import DecisionTreeClassifier
            dt_model = DecisionTreeClassifier(
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
            dt_model.fit(X_train, y_train)
            y_pred = dt_model.predict(X_test)
            acc = accuracy_score(y_test, y_pred)
            cm = confusion_matrix(y_test, y_pred).tolist()
            report = classification_report(y_test, y_pred, output_dict=True)
            importances = dict(zip(feature_names, [float(v) for v in dt_model.feature_importances_]))

            model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'decision_tree_model.pkl')
            joblib.dump(dt_model, model_path)

            model_report['decision_tree'] = {
                'name': 'Decision Tree Classifier',
                'type': 'Tree-based',
                'accuracy': round(acc, 4),
                'precision': round(report['weighted avg']['precision'], 4),
                'recall': round(report['weighted avg']['recall'], 4),
                'f1_score': round(report['weighted avg']['f1-score'], 4),
                'confusion_matrix': cm,
                'feature_importances': importances,
                'hyperparameters': {
                    'max_depth': 10,
                    'min_samples_split': 5,
                    'min_samples_leaf': 2,
                    'criterion': 'gini',
                },
                'tree_depth': dt_model.get_depth(),
                'tree_leaves': dt_model.get_n_leaves(),
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'trained_at': datetime.now().isoformat(),
                'model_file': 'decision_tree_model.pkl',
            }
            self.stdout.write(self.style.SUCCESS(f"     OK Decision Tree - Accuracy: {acc:.4f} | Depth: {dt_model.get_depth()} | Leaves: {dt_model.get_n_leaves()}"))

        # ─── Random Forest ───
        if 'random_forest' in selected_models:
            self.stdout.write("  [+] Training Random Forest Classifier...")
            from sklearn.ensemble import RandomForestClassifier
            rf_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=12,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
            rf_model.fit(X_train, y_train)
            y_pred = rf_model.predict(X_test)
            acc = accuracy_score(y_test, y_pred)
            cm = confusion_matrix(y_test, y_pred).tolist()
            report = classification_report(y_test, y_pred, output_dict=True)
            importances = dict(zip(feature_names, [float(v) for v in rf_model.feature_importances_]))

            model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'random_forest_model.pkl')
            joblib.dump(rf_model, model_path)

            model_report['random_forest'] = {
                'name': 'Random Forest Classifier',
                'type': 'Ensemble (Bagging)',
                'accuracy': round(acc, 4),
                'precision': round(report['weighted avg']['precision'], 4),
                'recall': round(report['weighted avg']['recall'], 4),
                'f1_score': round(report['weighted avg']['f1-score'], 4),
                'confusion_matrix': cm,
                'feature_importances': importances,
                'hyperparameters': {
                    'n_estimators': 100,
                    'max_depth': 12,
                    'min_samples_split': 5,
                    'min_samples_leaf': 2,
                    'criterion': 'gini',
                },
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'trained_at': datetime.now().isoformat(),
                'model_file': 'random_forest_model.pkl',
            }
            self.stdout.write(self.style.SUCCESS(f"     OK Random Forest - Accuracy: {acc:.4f}"))

        # ─── Logistic Regression (Linear Model) ───
        if 'logistic_regression' in selected_models:
            self.stdout.write("  [+] Training Logistic Regression (Linear Model)...")
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler

            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            lr_model = LogisticRegression(
                max_iter=1000,
                solver='lbfgs',
                C=1.0,
                random_state=42
            )
            lr_model.fit(X_train_scaled, y_train)
            y_pred = lr_model.predict(X_test_scaled)
            acc = accuracy_score(y_test, y_pred)
            cm = confusion_matrix(y_test, y_pred).tolist()
            report = classification_report(y_test, y_pred, output_dict=True)

            # Coefficients as feature importance proxy
            coefficients = dict(zip(feature_names, [float(v) for v in lr_model.coef_[0]]))

            model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'logistic_regression_model.pkl')
            scaler_path = os.path.join(settings.BASE_DIR, 'ml_models', 'lr_scaler.pkl')
            joblib.dump(lr_model, model_path)
            joblib.dump(scaler, scaler_path)

            model_report['logistic_regression'] = {
                'name': 'Logistic Regression',
                'type': 'Linear Model',
                'accuracy': round(acc, 4),
                'precision': round(report['weighted avg']['precision'], 4),
                'recall': round(report['weighted avg']['recall'], 4),
                'f1_score': round(report['weighted avg']['f1-score'], 4),
                'confusion_matrix': cm,
                'feature_importances': coefficients,
                'hyperparameters': {
                    'solver': 'lbfgs',
                    'C': 1.0,
                    'max_iter': 1000,
                    'penalty': 'l2',
                },
                'intercept': float(lr_model.intercept_[0]),
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'trained_at': datetime.now().isoformat(),
                'model_file': 'logistic_regression_model.pkl',
            }
            self.stdout.write(self.style.SUCCESS(f"     OK Logistic Regression - Accuracy: {acc:.4f}"))

        # ── Save Report ────────────────────────────────────────────
        report_path = os.path.join(settings.BASE_DIR, 'ml_models', 'model_report.json')

        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (np.integer,)):
                    return int(obj)
                if isinstance(obj, (np.floating,)):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super().default(obj)

        with open(report_path, 'w') as f:
            json.dump(model_report, f, indent=2, cls=NumpyEncoder)

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("  All models trained successfully!"))
        self.stdout.write(f"  Report saved to: {report_path}")
        self.stdout.write("=" * 60)

        # Summary table
        self.stdout.write("\n  Model Comparison:")
        self.stdout.write("  " + "-" * 50)
        self.stdout.write(f"  {'Model':<28} {'Accuracy':>10} {'F1':>10}")
        self.stdout.write("  " + "-" * 50)
        for key, info in model_report.items():
            self.stdout.write(f"  {info['name']:<28} {info['accuracy']:>10.4f} {info['f1_score']:>10.4f}")
        self.stdout.write("  " + "-" * 50)
