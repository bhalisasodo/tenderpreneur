import argparse
import asyncio
from getpass import getpass

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.models import Organisation, SupplierProfile, User, utc_now
from app.core.security import hash_password


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provision a BoQPro organisation account after identity verification."
    )
    parser.add_argument("--organisation-type", choices=("contractor", "supplier"), required=True)
    parser.add_argument("--organisation-name", required=True)
    parser.add_argument("--organisation-email", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--user-name", required=True)
    parser.add_argument("--user-email", required=True)
    parser.add_argument(
        "--role",
        choices=("admin", "estimator", "sales", "platform_operator"),
        default="admin",
    )
    parser.add_argument("--categories", help="Comma-separated supplier categories; required for suppliers.")
    parser.add_argument("--service-regions", help="Comma-separated service areas; required for suppliers.")
    return parser.parse_args()


async def _create_account(args: argparse.Namespace, password: str) -> str:
    organisation_email = args.organisation_email.strip().lower()
    user_email = args.user_email.strip().lower()
    if args.role == "platform_operator" and args.organisation_type != "contractor":
        raise ValueError("Platform operator accounts must belong to a contractor-type organisation.")

    categories = [value.strip() for value in (args.categories or "").split(",") if value.strip()]
    service_regions = [value.strip() for value in (args.service_regions or "").split(",") if value.strip()]
    if args.organisation_type == "supplier" and (not categories or not service_regions):
        raise ValueError("Supplier accounts require explicit --categories and --service-regions.")

    async with AsyncSessionLocal() as db:
        existing_user = await db.scalar(select(User.id).where(User.email == user_email))
        if existing_user:
            raise ValueError("A user with that email address already exists.")
        existing_org = await db.scalar(select(Organisation.id).where(Organisation.email == organisation_email))
        if existing_org:
            raise ValueError("An organisation with that email address already exists.")

        now = utc_now()
        organisation = Organisation(
            type=args.organisation_type,
            legal_name=args.organisation_name.strip(),
            email=organisation_email,
            region=args.region.strip(),
            created_at=now,
            updated_at=now,
        )
        user = User(
            organisation=organisation,
            email=user_email,
            name=args.user_name.strip(),
            role=args.role,
            password_hash=hash_password(password),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add_all([organisation, user])

        if args.organisation_type == "supplier":
            db.add(
                SupplierProfile(
                    organisation=organisation,
                    categories=categories,
                    service_regions=service_regions,
                    compliance_flags={},
                    preferred_contact_method="email",
                    status="pending",
                    active=False,
                    created_at=now,
                    updated_at=now,
                )
            )

        await db.commit()
        return organisation.id


async def main() -> None:
    args = _parse_args()
    password = getpass("Temporary password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    try:
        organisation_id = await _create_account(args, password)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    print(f"Created {args.organisation_type} account for {args.user_email.strip().lower()}.")
    print(f"Organisation ID: {organisation_id}")
    if args.organisation_type == "supplier":
        print("Supplier access remains pending until an operator approves the profile.")


if __name__ == "__main__":
    asyncio.run(main())
