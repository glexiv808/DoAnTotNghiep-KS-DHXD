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
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, inspect, text, ForeignKey
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
    role = Column(String, default="user", nullable=False)  # "user" hoặc "admin"
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

# Token Blacklist Model
class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, ForeignKey("users.username"), index=True, nullable=False)
    blacklisted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

# Processing Session Model - để lưu các bản ghi đã xử lý
class ProcessingSession(Base):
    __tablename__ = "processing_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, ForeignKey("users.username"), index=True, nullable=False)
    session_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    row_count = Column(Integer, default=0)
    data = Column(String, nullable=False)  # JSON string chứa dữ liệu

# Processing Result Model - để lưu từng bản ghi
class ProcessingResult(Base):
    __tablename__ = "processing_results"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("processing_sessions.session_id"), index=True, nullable=False)
    username = Column(String, ForeignKey("users.username"), index=True, nullable=False)
    row_number = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    income = Column(String, nullable=True)
    score = Column(String, nullable=True)
    result = Column(String, nullable=True)
    contact_status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Loan Contract Model
class LoanContractDB(Base):
    __tablename__ = "loan_contracts"
    
    contractNumber = Column(String, primary_key=True, index=True, nullable=False)
    username = Column(String, ForeignKey("users.username"), index=True, nullable=False)  # Chủ sở hữu/người quản lý hợp đồng
    customerName = Column(String, nullable=False)
    loanAmount = Column(String, nullable=False)
    interestRate = Column(String, nullable=False)
    loanDuration = Column(String, nullable=False)
    createdDate = Column(String, nullable=False)
    status = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Notification Model - để thông báo cho người phụ trách khi admin chỉnh sửa
class NotificationDB(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, ForeignKey("users.username"), index=True, nullable=False)  # Người nhận notification
    contract_number = Column(String, ForeignKey("loan_contracts.contractNumber"), index=True, nullable=False)  # Hợp đồng bị chỉnh sửa
    edited_by = Column(String, ForeignKey("users.username"), nullable=False)  # Admin người chỉnh sửa
    changes = Column(String, nullable=False)  # JSON string chứa chi tiết thay đổi
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Tạo bảng
Base.metadata.create_all(bind=engine)

# Migration: Thêm cột username nếu chưa tồn tại
def add_username_column_if_not_exists():
    """Thêm cột username vào bảng loan_contracts nếu chưa tồn tại"""
    try:
        # Kiểm tra xem bảng có tồn tại không
        inspector_obj = inspect(engine)
        tables = inspector_obj.get_table_names()
        
        if 'loan_contracts' not in tables:
            logger.info("Bảng loan_contracts chưa tồn tại, không cần migration")
            return
        
        columns = inspector_obj.get_columns('loan_contracts')
        column_names = [col['name'] for col in columns]
        
        if 'username' not in column_names:
            with engine.connect() as conn:
                if 'sqlite' in DATABASE_URL:
                    # SQLite không hỗ trợ ALTER COLUMN, phải dùng cách khác
                    conn.execute(text(
                        'ALTER TABLE loan_contracts ADD COLUMN username VARCHAR(255) DEFAULT "unknown"'
                    ))
                else:
                    # PostgreSQL hoặc databases khác
                    conn.execute(text(
                        'ALTER TABLE loan_contracts ADD COLUMN username VARCHAR(255) DEFAULT "unknown"'
                    ))
                conn.commit()
                logger.info("Thêm cột username vào bảng loan_contracts thành công")
        else:
            logger.info("Cột username đã tồn tại")
    except Exception as e:
        logger.warning(f"Không thể kiểm tra/thêm cột username: {e}")

# Migration: Thêm cột role nếu chưa tồn tại
def add_role_column_if_not_exists():
    """Thêm cột role vào bảng users nếu chưa tồn tại"""
    try:
        inspector_obj = inspect(engine)
        tables = inspector_obj.get_table_names()
        
        if 'users' not in tables:
            logger.info("Bảng users chưa tồn tại, không cần migration")
            return
        
        columns = inspector_obj.get_columns('users')
        column_names = [col['name'] for col in columns]
        
        if 'role' not in column_names:
            with engine.connect() as conn:
                if 'sqlite' in DATABASE_URL:
                    conn.execute(text(
                        'ALTER TABLE users ADD COLUMN role VARCHAR(255) DEFAULT "user"'
                    ))
                else:
                    conn.execute(text(
                        'ALTER TABLE users ADD COLUMN role VARCHAR(255) DEFAULT "user"'
                    ))
                conn.commit()
                logger.info("Thêm cột role vào bảng users thành công")
        else:
            logger.info("Cột role đã tồn tại")
    except Exception as e:
        logger.warning(f"Không thể kiểm tra/thêm cột role: {e}")

# Chạy migration khi app khởi động
add_username_column_if_not_exists()
add_role_column_if_not_exists()

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
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None

class UserDetailResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    role: str
    created_at: datetime
    last_login: Optional[datetime]
    contracts_count: int = 0
    
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

# ==================== LOAN CONTRACT MODELS ====================
class LoanContract(BaseModel):
    contractNumber: str
    customerName: str
    loanAmount: float
    interestRate: float
    loanDuration: int
    createdDate: str
    status: str
    email: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

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

def get_admin_user(current_user: User = Depends(get_current_user)):
    """Kiểm tra xem user hiện tại có phải admin không"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access this resource"
        )
    return current_user

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
        full_name=user.full_name,
        role="user"  # Mặc định role là 'user'
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

# ==================== LOAN CONTRACT MANAGEMENT ENDPOINTS ====================
@app.get("/loans")
async def get_all_loans(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lấy tất cả hợp đồng vay. 
    - Nếu user là admin: lấy tất cả hợp đồng của tất cả user, bao gồm người tạo
    - Nếu user không phải admin: chỉ lấy hợp đồng của user hiện tại hoặc những hợp đồng được tạo trước khi có tính năng user
    """
    try:
        if current_user.role == "admin":
            # Admin xem tất cả hợp đồng
            loans = db.query(LoanContractDB).all()
        else:
            # User thường chỉ xem hợp đồng của chính mình
            loans = db.query(LoanContractDB).filter(
                (LoanContractDB.username == current_user.username) | 
                (LoanContractDB.username == "unknown")
            ).all()
        
        loans_data = []
        for loan in loans:
            loan_info = {
                'contractNumber': loan.contractNumber,
                'customerName': loan.customerName,
                'loanAmount': loan.loanAmount,
                'interestRate': loan.interestRate,
                'loanDuration': loan.loanDuration,
                'createdDate': loan.createdDate,
                'status': loan.status,
                'email': loan.email,
                'phone': loan.phone,
                'description': loan.description,
                'username': loan.username
            }
            # Thêm tên chủ sở hữu nếu user là admin
            if current_user.role == "admin":
                loan_info['createdBy'] = loan.username if loan.username != "unknown" else "Hệ thống"
            
            loans_data.append(loan_info)
        
        return {
            'loans': loans_data,
            'userRole': current_user.role
        }
    except Exception as e:
        logger.error(f"Error fetching loans: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch loans")

@app.get("/loans/{contractNumber}")
async def get_loan(contractNumber: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lấy chi tiết một hợp đồng. Admin xem được hợp đồng của bất kỳ user nào, user thường chỉ xem của chính mình"""
    try:
        loan = db.query(LoanContractDB).filter(
            LoanContractDB.contractNumber == contractNumber
        ).first()
        
        # Kiểm tra quyền truy cập
        if not loan:
            raise HTTPException(status_code=404, detail="Loan contract not found")
        
        if current_user.role != "admin" and loan.username != current_user.username:
            raise HTTPException(status_code=403, detail="You don't have permission to view this contract")
        
        return {
            'contractNumber': loan.contractNumber,
            'customerName': loan.customerName,
            'loanAmount': loan.loanAmount,
            'interestRate': loan.interestRate,
            'loanDuration': loan.loanDuration,
            'createdDate': loan.createdDate,
            'status': loan.status,
            'email': loan.email,
            'phone': loan.phone,
            'description': loan.description,
            'username': loan.username
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching loan: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch loan")

@app.post("/loans")
async def create_loan(loan: LoanContract, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Tạo hợp đồng vay mới (lưu user tạo)"""
    try:
        # Check if contract already exists
        existing = db.query(LoanContractDB).filter(LoanContractDB.contractNumber == loan.contractNumber).first()
        if existing:
            raise HTTPException(status_code=400, detail="Contract number already exists")
        
        # Create new loan contract
        new_loan = LoanContractDB(
            contractNumber=loan.contractNumber,
            username=current_user.username,  # Chủ sở hữu hợp đồng
            customerName=loan.customerName,
            loanAmount=str(loan.loanAmount),
            interestRate=str(loan.interestRate),
            loanDuration=str(loan.loanDuration),
            createdDate=loan.createdDate,
            status=loan.status,
            email=loan.email,
            phone=loan.phone,
            description=loan.description
        )
        
        db.add(new_loan)
        db.commit()
        db.refresh(new_loan)
        
        logger.info(f"New loan contract created: {loan.contractNumber} by {current_user.username}")
        
        return {
            'contractNumber': new_loan.contractNumber,
            'customerName': new_loan.customerName,
            'loanAmount': new_loan.loanAmount,
            'interestRate': new_loan.interestRate,
            'loanDuration': new_loan.loanDuration,
            'createdDate': new_loan.createdDate,
            'status': new_loan.status,
            'email': new_loan.email,
            'phone': new_loan.phone,
            'description': new_loan.description
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating loan: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create loan contract")

@app.put("/loans/{contractNumber}")
async def update_loan(contractNumber: str, loan: LoanContract, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cập nhật hợp đồng vay. Admin có thể sửa bất kỳ hợp đồng nào, user thường chỉ sửa của chính mình"""
    try:
        # Find existing contract
        existing_loan = db.query(LoanContractDB).filter(
            LoanContractDB.contractNumber == contractNumber
        ).first()
        
        if not existing_loan:
            raise HTTPException(status_code=404, detail="Loan contract not found")
        
        # Kiểm tra quyền truy cập
        if current_user.role != "admin" and existing_loan.username != current_user.username:
            raise HTTPException(status_code=403, detail="You don't have permission to update this contract")
        
        # Track changes
        changes = {}
        if existing_loan.customerName != loan.customerName:
            changes['customerName'] = {'old': existing_loan.customerName, 'new': loan.customerName}
        if existing_loan.loanAmount != str(loan.loanAmount):
            changes['loanAmount'] = {'old': existing_loan.loanAmount, 'new': str(loan.loanAmount)}
        if existing_loan.interestRate != str(loan.interestRate):
            changes['interestRate'] = {'old': existing_loan.interestRate, 'new': str(loan.interestRate)}
        if existing_loan.loanDuration != str(loan.loanDuration):
            changes['loanDuration'] = {'old': existing_loan.loanDuration, 'new': str(loan.loanDuration)}
        if existing_loan.createdDate != loan.createdDate:
            changes['createdDate'] = {'old': existing_loan.createdDate, 'new': loan.createdDate}
        if existing_loan.status != loan.status:
            changes['status'] = {'old': existing_loan.status, 'new': loan.status}
        if existing_loan.email != loan.email:
            changes['email'] = {'old': existing_loan.email, 'new': loan.email}
        if existing_loan.phone != loan.phone:
            changes['phone'] = {'old': existing_loan.phone, 'new': loan.phone}
        if existing_loan.description != loan.description:
            changes['description'] = {'old': existing_loan.description, 'new': loan.description}
        
        # Update fields
        existing_loan.customerName = loan.customerName
        existing_loan.loanAmount = str(loan.loanAmount)
        existing_loan.interestRate = str(loan.interestRate)
        existing_loan.loanDuration = str(loan.loanDuration)
        existing_loan.createdDate = loan.createdDate
        existing_loan.status = loan.status
        existing_loan.email = loan.email
        existing_loan.phone = loan.phone
        existing_loan.description = loan.description
        existing_loan.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_loan)
        
        # Nếu admin chỉnh sửa và có thay đổi, tạo notification cho người phụ trách
        if current_user.role == "admin" and changes and existing_loan.username != current_user.username:
            notification = NotificationDB(
                username=existing_loan.username,  # Người phụ trách hợp đồng
                contract_number=contractNumber,
                edited_by=current_user.username,  # Admin người chỉnh sửa
                changes=json.dumps(changes),
                is_read=False
            )
            db.add(notification)
            db.commit()
            logger.info(f"Notification created for {existing_loan.username} - Contract {contractNumber} updated by {current_user.username}")
        
        logger.info(f"Loan contract updated: {contractNumber} by {current_user.username}")
        
        return {
            'contractNumber': existing_loan.contractNumber,
            'customerName': existing_loan.customerName,
            'loanAmount': existing_loan.loanAmount,
            'interestRate': existing_loan.interestRate,
            'loanDuration': existing_loan.loanDuration,
            'createdDate': existing_loan.createdDate,
            'status': existing_loan.status,
            'email': existing_loan.email,
            'phone': existing_loan.phone,
            'description': existing_loan.description,
            'username': existing_loan.username
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating loan: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update loan contract")

@app.delete("/loans/{contractNumber}")
async def delete_loan(contractNumber: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Xóa hợp đồng vay (chỉ user sở hữu mới có thể xóa)"""
    try:
        # Find and delete contract - chỉ lấy của user hiện tại
        loan = db.query(LoanContractDB).filter(
            LoanContractDB.contractNumber == contractNumber,
            LoanContractDB.username == current_user.username
        ).first()
        if not loan:
            raise HTTPException(status_code=404, detail="Loan contract not found or you don't have permission")
        
        db.delete(loan)
        db.commit()
        
        logger.info(f"Loan contract deleted: {contractNumber} by {current_user.username}")
        
        return {
            'status': 'success',
            'message': f'Contract {contractNumber} deleted successfully'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting loan: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete loan contract")

@app.put("/loans/{contractNumber}/owner")
async def update_loan_owner(contractNumber: str, request_data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cập nhật chủ sở hữu hợp đồng (chỉ admin)"""
    try:
        # Kiểm tra quyền admin
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Only admin can change contract owner")
        
        # Tìm hợp đồng
        loan = db.query(LoanContractDB).filter(
            LoanContractDB.contractNumber == contractNumber
        ).first()
        
        if not loan:
            raise HTTPException(status_code=404, detail="Loan contract not found")
        
        # Lấy chủ sở hữu mới từ request
        new_owner = request_data.get("username")
        if not new_owner:
            raise HTTPException(status_code=400, detail="username is required")
        
        # Kiểm tra xem người dùng mới tồn tại không
        user_exists = db.query(User).filter(User.username == new_owner).first()
        if not user_exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Cập nhật chủ sở hữu
        loan.username = new_owner
        loan.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(loan)
        
        logger.info(f"Loan contract owner updated for {contractNumber} to {new_owner} by admin {current_user.username}")
        
        return {
            'status': 'success',
            'contractNumber': loan.contractNumber,
            'username': loan.username
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating loan owner: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update loan owner")

# ==================== ADMIN USER MANAGEMENT ENDPOINTS ====================
@app.get("/admin/users")
async def get_all_users(
    page: int = 1,
    per_page: int = 10,
    search: str = "",
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách tất cả người dùng (chỉ admin)"""
    try:
        offset = (page - 1) * per_page
        query = db.query(User)
        if search:
            query = query.filter(
                (User.username.ilike(f"%{search}%")) |
                (User.email.ilike(f"%{search}%")) |
                (User.full_name.ilike(f"%{search}%"))
            )
        total = query.count()
        users = query.order_by(User.created_at.desc()).offset(offset).limit(per_page).all()
        
        users_data = []
        for user in users:
            contract_count = db.query(LoanContractDB).filter(
                LoanContractDB.username == user.username
            ).count()
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'is_active': user.is_active,
                'role': user.role,
                'created_at': user.created_at.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'contracts_count': contract_count
            })
        
        logger.info(f"Admin {admin.username} retrieved user list")
        return {
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page,
            'users': users_data
        }
    except Exception as e:
        logger.error(f"Error retrieving users: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users")

@app.get("/admin/users/{user_id}")
async def get_user_detail(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Lấy chi tiết một người dùng và hợp đồng của họ (chỉ admin)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        contracts = db.query(LoanContractDB).filter(
            LoanContractDB.username == user.username
        ).all()
        
        contracts_data = []
        for contract in contracts:
            contracts_data.append({
                'contractNumber': contract.contractNumber,
                'customerName': contract.customerName,
                'loanAmount': contract.loanAmount,
                'interestRate': contract.interestRate,
                'loanDuration': contract.loanDuration,
                'createdDate': contract.createdDate,
                'status': contract.status,
                'email': contract.email,
                'phone': contract.phone,
                'description': contract.description,
                'created_at': contract.created_at.isoformat()
            })
        
        logger.info(f"Admin {admin.username} retrieved details for user {user.username}")
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'is_active': user.is_active,
            'role': user.role,
            'created_at': user.created_at.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'contracts_count': len(contracts_data),
            'contracts': contracts_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user details: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user details")

@app.put("/admin/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Cập nhật thông tin người dùng (chỉ admin)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if admin.id == user_id and user_data.role and user_data.role != "admin":
            raise HTTPException(status_code=400, detail="You cannot change your own role")
        
        if user_data.email:
            existing = db.query(User).filter(
                User.email == user_data.email,
                User.id != user_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Email already registered")
            user.email = user_data.email
        
        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        if user_data.role and user_data.role in ["user", "admin"]:
            user.role = user_data.role
        
        db.commit()
        db.refresh(user)
        logger.info(f"Admin {admin.username} updated user {user.username}")
        
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'is_active': user.is_active,
            'role': user.role,
            'created_at': user.created_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update user")

@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Xóa người dùng (chỉ admin)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if admin.id == user_id:
            raise HTTPException(status_code=400, detail="You cannot delete your own account")
        
        db.query(LoanContractDB).filter(
            LoanContractDB.username == user.username
        ).delete()
        
        db.delete(user)
        db.commit()
        logger.info(f"Admin {admin.username} deleted user {user.username}")
        
        return {
            'status': 'success',
            'message': f'User {user.username} deleted successfully'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete user")

@app.post("/admin/users")
async def create_user_by_admin(
    user: UserCreate,
    role: str = "user",
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Tạo user mới bởi admin"""
    try:
        db_user = db.query(User).filter(User.username == user.username).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        db_user = db.query(User).filter(User.email == user.email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        if role not in ["user", "admin"]:
            role = "user"
        
        hashed_password = get_password_hash(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            full_name=user.full_name,
            role=role
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"Admin {admin.username} created new user {user.username} with role {role}")
        return {
            'id': db_user.id,
            'username': db_user.username,
            'email': db_user.email,
            'full_name': db_user.full_name,
            'is_active': db_user.is_active,
            'role': db_user.role,
            'created_at': db_user.created_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create user")

@app.get("/admin/stats")
async def get_admin_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Lấy thống kê hệ thống (chỉ admin)"""
    try:
        total_users = db.query(User).count()
        admin_users = db.query(User).filter(User.role == "admin").count()
        regular_users = db.query(User).filter(User.role == "user").count()
        active_users = db.query(User).filter(User.is_active == True).count()
        total_contracts = db.query(LoanContractDB).count()
        
        logger.info(f"Admin {admin.username} retrieved system stats")
        return {
            'total_users': total_users,
            'admin_users': admin_users,
            'regular_users': regular_users,
            'active_users': active_users,
            'total_contracts': total_contracts
        }
    except Exception as e:
        logger.error(f"Error retrieving stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")

@app.post("/create-first-admin")
async def create_first_admin(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """Tạo tài khoản admin đầu tiên (chỉ hoạt động khi chưa có admin nào)"""
    try:
        # Kiểm tra có admin nào không
        existing_admin = db.query(User).filter(User.role == "admin").first()
        if existing_admin:
            raise HTTPException(
                status_code=400,
                detail="Admin account already exists. Use /admin/users endpoint to create more admins."
            )
        
        # Kiểm tra username đã tồn tại
        db_user = db.query(User).filter(User.username == user.username).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        # Kiểm tra email đã tồn tại
        db_user = db.query(User).filter(User.email == user.email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Tạo user mới với role admin
        hashed_password = get_password_hash(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            full_name=user.full_name,
            role="admin"  # Admin đầu tiên
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"First admin account created: {user.username}")
        
        return {
            'status': 'success',
            'message': f'Admin account "{user.username}" created successfully',
            'id': db_user.id,
            'username': db_user.username,
            'email': db_user.email,
            'role': db_user.role
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating first admin: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create admin account")

# ==================== NOTIFICATION ENDPOINTS ====================

@app.get("/notifications")
async def get_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lấy danh sách thông báo cho người dùng hiện tại"""
    try:
        notifications = db.query(NotificationDB).filter(
            NotificationDB.username == current_user.username
        ).order_by(NotificationDB.created_at.desc()).all()
        
        notifications_data = []
        for notif in notifications:
            changes = json.loads(notif.changes)
            notifications_data.append({
                'id': notif.id,
                'contract_number': notif.contract_number,
                'edited_by': notif.edited_by,
                'changes': changes,
                'is_read': notif.is_read,
                'created_at': notif.created_at.isoformat()
            })
        
        # Get unread count
        unread_count = db.query(NotificationDB).filter(
            NotificationDB.username == current_user.username,
            NotificationDB.is_read == False
        ).count()
        
        logger.info(f"User {current_user.username} retrieved notifications")
        return {
            'notifications': notifications_data,
            'unread_count': unread_count
        }
    except Exception as e:
        logger.error(f"Error retrieving notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notifications")

@app.put("/notifications/{notification_id}/mark-as-read")
async def mark_notification_as_read(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Đánh dấu thông báo là đã đọc"""
    try:
        notification = db.query(NotificationDB).filter(
            NotificationDB.id == notification_id,
            NotificationDB.username == current_user.username
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        notification.is_read = True
        db.commit()
        
        logger.info(f"Notification {notification_id} marked as read by {current_user.username}")
        return {'status': 'success', 'message': 'Notification marked as read'}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")

@app.put("/notifications/mark-all-as-read")
async def mark_all_notifications_as_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Đánh dấu tất cả thông báo là đã đọc"""
    try:
        db.query(NotificationDB).filter(
            NotificationDB.username == current_user.username,
            NotificationDB.is_read == False
        ).update({NotificationDB.is_read: True})
        db.commit()
        
        logger.info(f"All notifications marked as read for {current_user.username}")
        return {'status': 'success', 'message': 'All notifications marked as read'}
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to mark notifications as read")

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