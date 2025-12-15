import time
import logging
import joblib
import numpy as np
import json
from typing import List, Optional
from functools import wraps
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from fastapi.middleware.cors import CORSMiddleware

# Import OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.trace import get_tracer_provider, set_tracer_provider

# Import Prometheus client
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
from contextlib import asynccontextmanager 

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CẤU HÌNH ====================
SECRET_KEY = "matkhausieudaihahahahahahahahahahahahahahahahahahahahahahaha"  # Thay đổi trong production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Database URL - có thể thay đổi sang PostgreSQL
DATABASE_URL = "sqlite:///./ml_service.db"  # Hoặc: "postgresql://user:pass@localhost/dbname"

# ==================== DATABASE SETUP ====================
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# User Model
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

# Token Blacklist Model
class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, index=True, nullable=False)
    blacklisted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

# Processing Session Model - để lưu các bản ghi đã xử lý
class ProcessingSession(Base):
    __tablename__ = "processing_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True, nullable=False)
    session_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    row_count = Column(Integer, default=0)
    data = Column(String, nullable=False)  # JSON string chứa dữ liệu

# Processing Result Model - để lưu từng bản ghi
class ProcessingResult(Base):
    __tablename__ = "processing_results"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    username = Column(String, index=True, nullable=False)
    row_number = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    income = Column(String, nullable=True)
    score = Column(String, nullable=True)
    result = Column(String, nullable=True)
    contact_status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Tạo bảng
Base.metadata.create_all(bind=engine)

# ==================== PYDANTIC MODELS ====================
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==================== PYDANTIC MODELS FOR SAVE/LOAD ====================
class ResultRecord(BaseModel):
    rowNumber: int
    name: str
    income: str
    score: str
    result: str
    contactStatus: str

class SaveResultsRequest(BaseModel):
    results: List[ResultRecord]

# ==================== SECURITY ====================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_token_blacklisted(token: str, db: Session) -> bool:
    """Kiểm tra token có trong blacklist không"""
    blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.token == token).first()
    return blacklisted is not None

def blacklist_token(token: str, username: str, exp_time: datetime, db: Session):
    """Thêm token vào blacklist khi logout"""
    blacklist_entry = TokenBlacklist(
        token=token,
        username=username,
        expires_at=exp_time
    )
    db.add(blacklist_entry)
    db.commit()

# ==================== DATABASE HELPER FUNCTIONS ====================
def save_processing_session(username: str, session_id: str, results: List[dict], db: Session):
    """Lưu phiên xử lý vào database"""
    try:
        session_data = json.dumps(results)
        processing_session = ProcessingSession(
            username=username,
            session_id=session_id,
            row_count=len(results),
            data=session_data
        )
        db.add(processing_session)
        db.commit()
        logger.info(f"Session {session_id} saved for user {username}")
        return True
    except Exception as e:
        logger.error(f"Error saving session to DB: {e}")
        db.rollback()
        return False

def load_user_sessions(username: str, db: Session):
    """Lấy tất cả sessions của user từ database"""
    try:
        sessions = db.query(ProcessingSession).filter(
            ProcessingSession.username == username
        ).order_by(ProcessingSession.created_at.desc()).all()
        
        sessions_list = []
        for session in sessions:
            sessions_list.append({
                'id': session.session_id,
                'timestamp': session.created_at.isoformat(),
                'rowCount': session.row_count,
                'results': json.loads(session.data)
            })
        
        logger.info(f"Loaded {len(sessions_list)} sessions for user {username}")
        return sessions_list
    except Exception as e:
        logger.error(f"Error loading sessions from DB: {e}")
        return []

def delete_user_session(session_id: str, username: str, db: Session):
    """Xóa một session khỏi database"""
    try:
        session = db.query(ProcessingSession).filter(
            ProcessingSession.session_id == session_id,
            ProcessingSession.username == username
        ).first()
        
        if session:
            db.delete(session)
            db.commit()
            logger.info(f"Session {session_id} deleted for user {username}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        db.rollback()
        return False

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        
        # Kiểm tra token có trong blacklist không
        if is_token_blacklisted(token, db):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

# ==================== OPENTELEMETRY SETUP ====================
resource = Resource.create({SERVICE_NAME: "ml-prediction-service"})

set_tracer_provider(TracerProvider(resource=resource))

jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger.monitoring.svc.cluster.local",
    agent_port=6831,
)

trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

tracer = get_tracer_provider().get_tracer("ml-prediction", "0.1.2")

# ==================== METRICS ====================
model_request_counter = Counter(
    'model_request_total',
    'Total number of requests sent to model',
    ['endpoint', 'user']
)

prediction_duration_histogram = Histogram(
    'ml_prediction_duration_seconds',
    'Time spent on predictions',
    ['endpoint', 'status', 'user']
)

error_counter = Counter(
    'ml_errors_total',
    'Total number of errors',
    ['operation', 'error_type']
)

auth_counter = Counter(
    'auth_requests_total',
    'Total authentication requests',
    ['operation', 'status']
)

# ==================== LIFESPAN ====================
cached_model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Service starting...")
    global cached_model
    try:
        cached_model = load_model()
        logger.info("✓ Main model (model_ml.joblib) loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load main model during startup: {e}")
    
    # Load comparison models
    try:
        load_all_models()
        logger.info("✓ All comparison models loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load comparison models during startup: {e}")
    
    yield
    
    logger.info("Shutting down ML Prediction Service...")
    cached_model = None

# ==================== FASTAPI APP ====================
app = FastAPI(
    title="ML Prediction Service with Auth",
    version="0.2.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Hoặc chỉ định cụ thể: ["http://127.0.0.1:5500"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== TRACING DECORATOR ====================
def trace_span(span_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
        return wrapper
    return decorator

# ==================== MODEL FUNCTIONS ====================
# @trace_span("model-loader")
def load_model():
    try:
        model = joblib.load("jupiter_notebook/model_ml.joblib")
        return model
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        error_counter.labels(operation="model_load", error_type=type(e).__name__).inc()
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

# @trace_span("predictor")
def make_prediction(model, features, username: str):
    start_time = time.time()
    
    try:
        logger.info(f"Making prediction for user {username} with features: {features}")
        
        if not features:
            raise ValueError("Features cannot be empty")
        
        features_array = np.array([features])
        prediction = model.predict(features_array)
        
        logger.info(f"Prediction result: {prediction}")
        result = prediction.tolist()
        
        duration = time.time() - start_time
        prediction_duration_histogram.labels(
            endpoint="internal", 
            status="success", 
            user=username
        ).observe(duration)
        
        return result
        
    except Exception as e:
        logger.error(f"Error making prediction: {e}")
        
        duration = time.time() - start_time
        prediction_duration_histogram.labels(
            endpoint="internal", 
            status="error", 
            user=username
        ).observe(duration)
        error_counter.labels(operation="prediction", error_type=type(e).__name__).inc()
        
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

# ==================== MODELS FOR COMPARISON ====================
cached_models = {
    'xgboost': None,
    'random_forest': None,
    'logistic_regression': None,
    'scaler_lr': None
}

def load_all_models():
    """Load tất cả 3 mô hình"""
    global cached_models
    try:
        cached_models['xgboost'] = joblib.load("jupiter_notebook/model_xgboost.joblib")
        logger.info("✓ Loaded XGBoost model")
        
        cached_models['random_forest'] = joblib.load("jupiter_notebook/model_random_forest.joblib")
        logger.info("✓ Loaded Random Forest model")
        
        cached_models['logistic_regression'] = joblib.load("jupiter_notebook/model_logistic_regression.joblib")
        logger.info("✓ Loaded Logistic Regression model")
        
        cached_models['scaler_lr'] = joblib.load("jupiter_notebook/scaler_logistic_regression.joblib")
        logger.info("✓ Loaded Logistic Regression scaler")
        
        return True
    except Exception as e:
        logger.error(f"Error loading models: {e}")
        return False

def predict_with_model(model_name: str, features_array):
    """Thực hiện dự đoán với một mô hình cụ thể"""
    try:
        if model_name == 'xgboost':
            return cached_models['xgboost'].predict(features_array)
        elif model_name == 'random_forest':
            return cached_models['random_forest'].predict(features_array)
        elif model_name == 'logistic_regression':
            features_scaled = cached_models['scaler_lr'].transform(features_array)
            return cached_models['logistic_regression'].predict(features_scaled)
        else:
            raise ValueError(f"Unknown model: {model_name}")
    except Exception as e:
        logger.error(f"Error predicting with {model_name}: {e}")
        raise

# ==================== AUTH ENDPOINTS ====================
@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Đăng ký user mới"""
    auth_counter.labels(operation="register", status="attempt").inc()
    
    # Kiểm tra username đã tồn tại
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        auth_counter.labels(operation="register", status="failed").inc()
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Kiểm tra email đã tồn tại
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        auth_counter.labels(operation="register", status="failed").inc()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Tạo user mới
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    auth_counter.labels(operation="register", status="success").inc()
    logger.info(f"New user registered: {user.username}")
    
    return db_user

@app.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Đăng nhập và nhận token"""
    auth_counter.labels(operation="login", status="attempt").inc()
    
    user = db.query(User).filter(User.username == user_credentials.username).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        auth_counter.labels(operation="login", status="failed").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Cập nhật last_login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Tạo access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    auth_counter.labels(operation="login", status="success").inc()
    logger.info(f"User logged in: {user.username}")
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Đăng xuất và vô hiệu hóa token"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        exp_time = datetime.utcfromtimestamp(payload.get("exp"))
        
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Kiểm tra token đã trong blacklist chưa
        if is_token_blacklisted(token, db):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token already revoked"
            )
        
        # Thêm token vào blacklist
        blacklist_token(token, username, exp_time, db)
        
        auth_counter.labels(operation="logout", status="success").inc()
        logger.info(f"User logged out: {username}")
        
        return {
            "status": "success",
            "message": "Logged out successfully",
            "username": username
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        auth_counter.labels(operation="logout", status="failed").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

@app.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin user hiện tại"""
    return current_user

# ==================== PREDICTION ENDPOINT ====================
@app.post("/predict")
def predict(
    features: List[float],
    current_user: User = Depends(get_current_user)
):
    """Thực hiện dự đoán (yêu cầu authentication)"""
    endpoint_start_time = time.time()
    
    model_request_counter.labels(endpoint="/predict", user=current_user.username).inc()
    
    # Validate credit_score (index 11 in FIELD_LIST: person_age, person_gender, person_education, person_income, person_emp_exp, person_home_ownership, loan_amnt, loan_intent, loan_int_rate, loan_percent_income, cb_person_cred_hist_length, credit_score, previous_loan_defaults_on_file)
    if len(features) > 11:
        credit_score_normalized = features[11]
        # Denormalize to check original value: original = (normalized * scale) + mean
        # Using scaler config: credit_score: { mean: 650, scale: 50 }
        credit_score_original = (credit_score_normalized * 50) + 650
        if credit_score_original < 300 or credit_score_original > 850:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credit score must be between 300 and 850"
            )
    
    try:
        with tracer.start_as_current_span("prediction-endpoint") as span:
            logger.info(f"User {current_user.username} requested prediction with features: {features}")
            
            span.set_attribute("user.username", current_user.username)
            span.set_attribute("input.features", str(features))
            span.set_attribute("input.length", len(features))
            
            model = load_model()
            prediction = make_prediction(model, features, current_user.username)
            
            span.set_attribute("prediction.result", str(prediction))
            span.set_attribute("prediction.success", True)
            
            endpoint_duration = time.time() - endpoint_start_time
            prediction_duration_histogram.labels(
                endpoint="/predict", 
                status="success", 
                user=current_user.username
            ).observe(endpoint_duration)
            
            logger.info(f"Returning prediction to {current_user.username}: {prediction}")
            return {
                "prediction": prediction,
                "status": "success",
                "user": current_user.username
            }
            
    except HTTPException as he:
        endpoint_duration = time.time() - endpoint_start_time
        prediction_duration_histogram.labels(
            endpoint="/predict", 
            status="http_error", 
            user=current_user.username
        ).observe(endpoint_duration)
        error_counter.labels(operation="endpoint", error_type="HTTPException").inc()
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in prediction endpoint: {e}")
        
        endpoint_duration = time.time() - endpoint_start_time
        prediction_duration_histogram.labels(
            endpoint="/predict", 
            status="error", 
            user=current_user.username
        ).observe(endpoint_duration)
        error_counter.labels(operation="endpoint", error_type=type(e).__name__).inc()
        
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ==================== EVALUATION ENDPOINT ====================
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

class EvaluationRequest(BaseModel):
    """Model cho dữ liệu kiểm thử"""
    pass

@app.post("/evaluate")
def evaluate_models(
    data: List[dict],
    current_user: User = Depends(get_current_user)
):
    """
    So sánh 3 mô hình ML trên một tập dữ liệu kiểm thử
    
    Dữ liệu yêu cầu: danh sách các bản ghi với features và label thực tế
    """
    endpoint_start_time = time.time()
    model_request_counter.labels(endpoint="/evaluate", user=current_user.username).inc()
    
    try:
        with tracer.start_as_current_span("evaluation-endpoint") as span:
            logger.info(f"User {current_user.username} requested model evaluation with {len(data)} samples")
            
            if len(data) == 0:
                raise ValueError("No data provided for evaluation")
            
            # Load all 3 models if not cached
            if not all([cached_models[m] for m in ['xgboost', 'random_forest', 'logistic_regression']]):
                load_all_models()
            
            # Danh sách features
            feature_cols = [
                'person_age', 'person_gender', 'person_education', 'person_income',
                'person_emp_exp', 'person_home_ownership', 'loan_amnt', 'loan_intent',
                'loan_int_rate', 'loan_percent_income', 'cb_person_cred_hist_length',
                'credit_score', 'previous_loan_defaults_on_file'
            ]
            
            # Chuyển đổi dữ liệu
            import pandas as pd
            df = pd.DataFrame(data)
            
            # Normalize column names to lowercase
            df.columns = df.columns.str.lower().str.strip()
            
            logger.info(f"DataFrame columns: {df.columns.tolist()}")
            logger.info(f"DataFrame head:\n{df.head()}")
            
            # Kiểm tra xem có cột target không (loan_status, target, y, v.v.)
            target_col = None
            for col in ['loan_status', 'target', 'y']:
                if col in df.columns:
                    target_col = col
                    break
            
            if target_col is None:
                raise ValueError(f"Dataset must contain a target column (loan_status, target, or y). Available columns: {df.columns.tolist()}")
            
            logger.info(f"Target column found: {target_col}")
            
            # Lấy X và y từ DataFrame
            X = df[feature_cols].copy()
            y_true = df[target_col].values
            
            logger.info(f"X shape before processing: {X.shape}")
            logger.info(f"X dtypes:\n{X.dtypes}")
            
            # Xử lý giá trị NaN cho numeric columns
            numeric_cols = X.select_dtypes(include=[np.number]).columns
            X[numeric_cols] = X[numeric_cols].fillna(X[numeric_cols].mean())
            
            # Xử lý giá trị NaN và categorical columns
            categorical_cols = X.select_dtypes(include=['object']).columns
            logger.info(f"Categorical columns: {categorical_cols.tolist()}")
            
            for col in categorical_cols:
                logger.info(f"Processing categorical column '{col}': {X[col].unique()[:5]}")
                X[col] = X[col].fillna(X[col].mode()[0] if len(X[col].mode()) > 0 else 'Unknown')
                # Chuyển đổi categorical thành numeric using factorize
                X[col] = pd.factorize(X[col])[0]
                logger.info(f"After factorize '{col}': {X[col].unique()}")
            
            # Chuyển thành numpy array
            X = X.values
            logger.info(f"X shape after processing: {X.shape}")
            
            # Thực hiện dự đoán với mỗi mô hình
            results = {}
            
            # XGBoost
            model_start = time.time()
            try:
                y_pred_xgb = predict_with_model('xgboost', X)
                xgb_time = (time.time() - model_start) * 1000  # Convert to ms
                
                results['xgboost'] = {
                    'accuracy': float(accuracy_score(y_true, y_pred_xgb)),
                    'precision': float(precision_score(y_true, y_pred_xgb, zero_division=0)),
                    'recall': float(recall_score(y_true, y_pred_xgb, zero_division=0)),
                    'f1': float(f1_score(y_true, y_pred_xgb, zero_division=0)),
                    'time': xgb_time
                }
                logger.info(f"XGBoost - Accuracy: {results['xgboost']['accuracy']:.4f}, Time: {xgb_time:.2f}ms")
            except Exception as e:
                logger.error(f"Error with XGBoost: {e}")
                results['xgboost'] = {
                    'accuracy': 0.0,
                    'precision': 0.0,
                    'recall': 0.0,
                    'f1': 0.0,
                    'time': 0.0,
                    'error': str(e)
                }
            
            # Random Forest
            model_start = time.time()
            try:
                y_pred_rf = predict_with_model('random_forest', X)
                rf_time = (time.time() - model_start) * 1000
                
                results['random_forest'] = {
                    'accuracy': float(accuracy_score(y_true, y_pred_rf)),
                    'precision': float(precision_score(y_true, y_pred_rf, zero_division=0)),
                    'recall': float(recall_score(y_true, y_pred_rf, zero_division=0)),
                    'f1': float(f1_score(y_true, y_pred_rf, zero_division=0)),
                    'time': rf_time
                }
                logger.info(f"Random Forest - Accuracy: {results['random_forest']['accuracy']:.4f}, Time: {rf_time:.2f}ms")
            except Exception as e:
                logger.error(f"Error with Random Forest: {e}")
                results['random_forest'] = {
                    'accuracy': 0.0,
                    'precision': 0.0,
                    'recall': 0.0,
                    'f1': 0.0,
                    'time': 0.0,
                    'error': str(e)
                }
            
            # Logistic Regression
            model_start = time.time()
            try:
                y_pred_lr = predict_with_model('logistic_regression', X)
                lr_time = (time.time() - model_start) * 1000
                
                results['logistic_regression'] = {
                    'accuracy': float(accuracy_score(y_true, y_pred_lr)),
                    'precision': float(precision_score(y_true, y_pred_lr, zero_division=0)),
                    'recall': float(recall_score(y_true, y_pred_lr, zero_division=0)),
                    'f1': float(f1_score(y_true, y_pred_lr, zero_division=0)),
                    'time': lr_time
                }
                logger.info(f"Logistic Regression - Accuracy: {results['logistic_regression']['accuracy']:.4f}, Time: {lr_time:.2f}ms")
            except Exception as e:
                logger.error(f"Error with Logistic Regression: {e}")
                results['logistic_regression'] = {
                    'accuracy': 0.0,
                    'precision': 0.0,
                    'recall': 0.0,
                    'f1': 0.0,
                    'time': 0.0,
                    'error': str(e)
                }
            
            endpoint_duration = time.time() - endpoint_start_time
            prediction_duration_histogram.labels(
                endpoint="/evaluate", 
                status="success", 
                user=current_user.username
            ).observe(endpoint_duration)
            
            logger.info(f"Evaluation completed for user {current_user.username}")
            
            return {
                'status': 'success',
                'user': current_user.username,
                'samples': len(data),
                'xgboost': results['xgboost'],
                'random_forest': results['random_forest'],
                'logistic_regression': results['logistic_regression']
            }
    
    except Exception as e:
        logger.error(f"Evaluation error: {e}")
        endpoint_duration = time.time() - endpoint_start_time
        prediction_duration_histogram.labels(
            endpoint="/evaluate", 
            status="error", 
            user=current_user.username
        ).observe(endpoint_duration)
        error_counter.labels(operation="evaluate", error_type=type(e).__name__).inc()
        
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

# ==================== SAVE/LOAD RESULTS ENDPOINTS ====================
@app.post("/save-results")
def save_results(
    results: List[ResultRecord],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lưu kết quả dự đoán vào database"""
    try:
        if not results:
            raise HTTPException(status_code=400, detail="Results cannot be empty")
        
        session_id = f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Chuyển kết quả thành dictionary
        results_dict = [result.dict() for result in results]
        
        if save_processing_session(current_user.username, session_id, results_dict, db):
            return {
                'success': True,
                'session_id': session_id,
                'message': f'Lưu thành công {len(results)} bản ghi',
                'timestamp': datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save to database")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in save_results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/load-results")
def load_results(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Load tất cả sessions đã lưu của user từ database"""
    try:
        sessions = load_user_sessions(current_user.username, db)
        
        if not sessions:
            return {
                'success': False,
                'message': 'Không có dữ liệu đã lưu',
                'sessions': []
            }
        
        return {
            'success': True,
            'sessions': sessions,
            'message': f'Tìm thấy {len(sessions)} phiên lưu'
        }
        
    except Exception as e:
        logger.error(f"Error in load_results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/load-session/{session_id}")
def load_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Load một session cụ thể từ database"""
    try:
        session = db.query(ProcessingSession).filter(
            ProcessingSession.session_id == session_id,
            ProcessingSession.username == current_user.username
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            'success': True,
            'session_id': session_id,
            'timestamp': session.created_at.isoformat(),
            'results': json.loads(session.data),
            'rowCount': session.row_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in load_session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete-session/{session_id}")
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xóa một session khỏi database"""
    try:
        if delete_user_session(session_id, current_user.username, db):
            return {
                'success': True,
                'message': 'Xóa phiên lưu thành công'
            }
        else:
            raise HTTPException(status_code=404, detail="Session not found or you don't have permission to delete")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== METRICS & HEALTH ====================
@app.get("/metrics")
def get_metrics():
    """Endpoint để Prometheus scrape metrics"""
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

@app.get("/")
def root():
    return {
        "message": "ML Prediction Service with Authentication",
        "version": "0.2.0",
        "endpoints": {
            "register": "/register",
            "login": "/login",
            "logout": "/logout (requires auth)",
            "predict": "/predict (requires auth)",
            "evaluate": "/evaluate (requires auth) - Compare 3 ML models",
            "user_info": "/users/me (requires auth)",
            "save_results": "/save-results (POST, requires auth) - Save prediction results to database",
            "load_results": "/load-results (GET, requires auth) - Load all user's saved sessions",
            "load_session": "/load-session/{session_id} (GET, requires auth) - Load specific session",
            "delete_session": "/delete-session/{session_id} (DELETE, requires auth) - Delete a session",
            "health": "/health",
            "metrics": "/metrics"
        }
    }

@app.get("/health")
def health():
    try:
        model_loaded = False
        try:
            load_model()
            model_loaded = True
        except:
            pass
        
        return {
            "status": "healthy",
            "model_loaded": model_loaded,
            "service": "ml-prediction-service",
            "database": "connected",
            "metrics_endpoint": "/metrics"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting ML Prediction Service with Authentication...")
    uvicorn.run(app, host="0.0.0.0", port=5000)