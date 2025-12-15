"""
Script để huấn luyện 3 mô hình ML (XGBoost, Random Forest, Logistic Regression)
và lưu chúng để sử dụng trong ứng dụng
"""

import joblib
import logging
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import warnings
warnings.filterwarnings('ignore')

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_data(csv_path="jupiter_notebook/loan_data.csv"):
    """Load dữ liệu từ CSV"""
    logger.info(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    logger.info(f"Data shape: {df.shape}")
    return df

def prepare_data(df):
    """Chuẩn bị dữ liệu cho training"""
    logger.info("Preparing data...")
    
    # Danh sách các cột feature
    feature_cols = [
        'person_age', 'person_gender', 'person_education', 'person_income',
        'person_emp_exp', 'person_home_ownership', 'loan_amnt', 'loan_intent',
        'loan_int_rate', 'loan_percent_income', 'cb_person_cred_hist_length',
        'credit_score', 'previous_loan_defaults_on_file'
    ]
    
    # Kiểm tra cột target (có thể là 'loan_status' hoặc 'target')
    target_col = None
    for col in ['loan_status', 'target', 'y']:
        if col in df.columns:
            target_col = col
            break
    
    if target_col is None:
        raise ValueError("Không tìm thấy cột target (loan_status/target/y)")
    
    logger.info(f"Target column: {target_col}")
    
    X = df[feature_cols].copy()
    y = df[target_col].copy()
    
    # Xử lý giá trị NaN cho numeric columns
    numeric_cols = X.select_dtypes(include=[np.number]).columns
    X[numeric_cols] = X[numeric_cols].fillna(X[numeric_cols].mean())
    
    # Xử lý giá trị NaN cho categorical columns (dùng mode)
    categorical_cols = X.select_dtypes(include=['object']).columns
    for col in categorical_cols:
        X[col] = X[col].fillna(X[col].mode()[0] if len(X[col].mode()) > 0 else 'Unknown')
    
    y = y.fillna(y.mode()[0] if len(y.mode()) > 0 else y.iloc[0])
    
    # Chuyển đổi categorical columns thành numeric
    for col in categorical_cols:
        X[col] = pd.factorize(X[col])[0]
    
    logger.info(f"Features shape: {X.shape}, Target shape: {y.shape}")
    logger.info(f"Data types:\n{X.dtypes}")
    
    return X, y, feature_cols

def train_models(X_train, X_test, y_train, y_test):
    """Huấn luyện 3 mô hình"""
    models = {}
    results = {}
    
    # 1. XGBoost
    logger.info("\n=== Training XGBoost ===")
    xgb = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    xgb.fit(X_train, y_train)
    models['xgboost'] = xgb
    
    y_pred_xgb = xgb.predict(X_test)
    results['xgboost'] = {
        'accuracy': accuracy_score(y_test, y_pred_xgb),
        'precision': precision_score(y_test, y_pred_xgb, zero_division=0),
        'recall': recall_score(y_test, y_pred_xgb, zero_division=0),
        'f1': f1_score(y_test, y_pred_xgb, zero_division=0)
    }
    logger.info(f"XGBoost Accuracy: {results['xgboost']['accuracy']:.4f}")
    
    # 2. Random Forest
    logger.info("\n=== Training Random Forest ===")
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    models['random_forest'] = rf
    
    y_pred_rf = rf.predict(X_test)
    results['random_forest'] = {
        'accuracy': accuracy_score(y_test, y_pred_rf),
        'precision': precision_score(y_test, y_pred_rf, zero_division=0),
        'recall': recall_score(y_test, y_pred_rf, zero_division=0),
        'f1': f1_score(y_test, y_pred_rf, zero_division=0)
    }
    logger.info(f"Random Forest Accuracy: {results['random_forest']['accuracy']:.4f}")
    
    # 3. Logistic Regression
    logger.info("\n=== Training Logistic Regression ===")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    lr = LogisticRegression(
        max_iter=1000,
        random_state=42,
        n_jobs=-1
    )
    lr.fit(X_train_scaled, y_train)
    models['logistic_regression'] = {
        'model': lr,
        'scaler': scaler
    }
    
    y_pred_lr = lr.predict(X_test_scaled)
    results['logistic_regression'] = {
        'accuracy': accuracy_score(y_test, y_pred_lr),
        'precision': precision_score(y_test, y_pred_lr, zero_division=0),
        'recall': recall_score(y_test, y_pred_lr, zero_division=0),
        'f1': f1_score(y_test, y_pred_lr, zero_division=0)
    }
    logger.info(f"Logistic Regression Accuracy: {results['logistic_regression']['accuracy']:.4f}")
    
    return models, results

def save_models(models):
    """Lưu các mô hình"""
    logger.info("\n=== Saving Models ===")
    
    joblib.dump(models['xgboost'], 'jupiter_notebook/model_xgboost.joblib')
    logger.info("Saved: model_xgboost.joblib")
    
    joblib.dump(models['random_forest'], 'jupiter_notebook/model_random_forest.joblib')
    logger.info("Saved: model_random_forest.joblib")
    
    joblib.dump(models['logistic_regression']['model'], 'jupiter_notebook/model_logistic_regression.joblib')
    logger.info("Saved: model_logistic_regression.joblib")
    
    joblib.dump(models['logistic_regression']['scaler'], 'jupiter_notebook/scaler_logistic_regression.joblib')
    logger.info("Saved: scaler_logistic_regression.joblib")

def main():
    """Chạy quy trình training và lưu"""
    logger.info("Starting ML Models Training Pipeline...")
    
    # Load dữ liệu
    df = load_data()
    
    # Chuẩn bị dữ liệu
    X, y, feature_cols = prepare_data(df)
    
    # Chia dữ liệu train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    logger.info(f"Train set: {X_train.shape}, Test set: {X_test.shape}")
    
    # Huấn luyện các mô hình
    models, results = train_models(X_train, X_test, y_train, y_test)
    
    # Lưu các mô hình
    save_models(models)
    
    # In tóm tắt kết quả
    logger.info("\n=== MODEL COMPARISON RESULTS ===")
    logger.info("-" * 60)
    for model_name, metrics in results.items():
        logger.info(f"\n{model_name.upper()}")
        logger.info(f"  Accuracy:  {metrics['accuracy']:.4f}")
        logger.info(f"  Precision: {metrics['precision']:.4f}")
        logger.info(f"  Recall:    {metrics['recall']:.4f}")
        logger.info(f"  F1-Score:  {metrics['f1']:.4f}")
    logger.info("-" * 60)
    logger.info("\n✓ Training complete! Models saved to jupiter_notebook/")

if __name__ == "__main__":
    main()
