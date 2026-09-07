import asyncio
import os
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set test environment
os.environ["TENDERPRENEUR_ENVIRONMENT"] = "testing"
os.environ["TENDERPRENEUR_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["TENDERPRENEUR_STORAGE_TYPE"] = "local"
os.environ["TENDERPRENEUR_LOCAL_STORAGE_PATH"] = "./test_storage"

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.models import (
    BoQ,
    Document,
    LineItem,
    Organisation,
    Quote,
    QuoteRequest,
    QuoteRequestSupplier,
    SupplierProfile,
    User,
    generate_uuid,
    utc_now,
)
from app.core.security import create_access_token
from app.main import app

test_engine = create_async_engine(
    "sqlite+aiosqlite:///./test_tenderpreneur.db",
    connect_args={"check_same_thread": False},
    future=True,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture
async def init_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def client(init_test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def db_session(init_test_db):
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def seeded_entities(db_session: AsyncSession):
    now = utc_now()

    # Contractor
    contractor_org = Organisation(
        id=generate_uuid(),
        type="contractor",
        legal_name="Amandla Civils (Pty) Ltd",
        email="estimator@amandla.co.za",
        region="KwaZulu-Natal",
        created_at=now,
        updated_at=now,
    )
    db_session.add(contractor_org)

    contractor_user = User(
        id=generate_uuid(),
        organisation_id=contractor_org.id,
        email="estimator@amandla.co.za",
        name="Sipho Contractor",
        role="admin",
        created_at=now,
        updated_at=now,
    )
    db_session.add(contractor_user)

    # Supplier 1: Durban Builders (Building Materials, Concrete in KZN)
    supplier1_org = Organisation(
        id=generate_uuid(),
        type="supplier",
        legal_name="Durban Builders Hub",
        email="sales@durbanhub.co.za",
        phone="+27820000001",
        region="KwaZulu-Natal",
        created_at=now,
        updated_at=now,
    )
    db_session.add(supplier1_org)

    supplier1_user = User(
        id=generate_uuid(),
        organisation_id=supplier1_org.id,
        email="sales@durbanhub.co.za",
        name="Durban Hub Rep",
        role="admin",
        created_at=now,
        updated_at=now,
    )
    db_session.add(supplier1_user)

    supplier1_profile = SupplierProfile(
        id=generate_uuid(),
        organisation_id=supplier1_org.id,
        categories=["building-materials", "concrete"],
        service_regions=["KwaZulu-Natal"],
        compliance_flags={"csd_registered": True, "bbee_level": "1"},
        preferred_contact_method="whatsapp",
        active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(supplier1_profile)

    # Supplier 2: AfriReady (Concrete, Earthworks in KZN, Gauteng)
    supplier2_org = Organisation(
        id=generate_uuid(),
        type="supplier",
        legal_name="AfriReady Concrete Solutions",
        email="orders@afriready.co.za",
        phone="+27820000002",
        region="KwaZulu-Natal",
        created_at=now,
        updated_at=now,
    )
    db_session.add(supplier2_org)

    supplier2_user = User(
        id=generate_uuid(),
        organisation_id=supplier2_org.id,
        email="orders@afriready.co.za",
        name="AfriReady Rep",
        role="admin",
        created_at=now,
        updated_at=now,
    )
    db_session.add(supplier2_user)

    supplier2_profile = SupplierProfile(
        id=generate_uuid(),
        organisation_id=supplier2_org.id,
        categories=["concrete", "earthworks"],
        service_regions=["KwaZulu-Natal", "Gauteng"],
        compliance_flags={"csd_registered": True},
        preferred_contact_method="whatsapp",
        active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(supplier2_profile)

    # Other Contractor (Tenant isolation test)
    other_contractor_org = Organisation(
        id=generate_uuid(),
        type="contractor",
        legal_name="Rival Build Ltd",
        email="boss@rivalbuild.co.za",
        region="Gauteng",
        created_at=now,
        updated_at=now,
    )
    db_session.add(other_contractor_org)

    other_user = User(
        id=generate_uuid(),
        organisation_id=other_contractor_org.id,
        email="boss@rivalbuild.co.za",
        name="Rival Boss",
        role="admin",
        created_at=now,
        updated_at=now,
    )
    db_session.add(other_user)

    await db_session.commit()

    # Create tokens
    contractor_token = create_access_token(
        user_id=contractor_user.id,
        organisation_id=contractor_org.id,
        organisation_type="contractor",
        email=contractor_user.email,
    )
    supplier1_token = create_access_token(
        user_id=supplier1_user.id,
        organisation_id=supplier1_org.id,
        organisation_type="supplier",
        email=supplier1_user.email,
    )
    supplier2_token = create_access_token(
        user_id=supplier2_user.id,
        organisation_id=supplier2_org.id,
        organisation_type="supplier",
        email=supplier2_user.email,
    )
    other_token = create_access_token(
        user_id=other_user.id,
        organisation_id=other_contractor_org.id,
        organisation_type="contractor",
        email=other_user.email,
    )

    return {
        "contractor_org": contractor_org,
        "contractor_user": contractor_user,
        "contractor_token": contractor_token,
        "supplier1_org": supplier1_org,
        "supplier1_token": supplier1_token,
        "supplier2_org": supplier2_org,
        "supplier2_token": supplier2_token,
        "other_contractor_org": other_contractor_org,
        "other_token": other_token,
    }
