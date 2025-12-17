
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.models import Experiment, Variant
from fastapi.testclient import TestClient
from app.main import app


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    """Test client with database dependency override"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_experiment(db):
    experiment = Experiment(
        name="Test Experiment",
        description="A test experiment",
        status="active"
    )
    db.add(experiment)
    db.flush()
    
    variant_a = Variant(
        experiment_id=experiment.id,
        name="control",
        traffic_percentage=50.0
    )
    variant_b = Variant(
        experiment_id=experiment.id,
        name="variant_b",
        traffic_percentage=50.0
    )
    db.add(variant_a)
    db.add(variant_b)
    db.commit()
    db.refresh(experiment)
    
    return experiment

