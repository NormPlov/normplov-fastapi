import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.utils.security import get_password_hash
from datetime import datetime
from faker import Faker


fake = Faker()


# Function to create static ADMIN
async def init_roles_and_admin(db: AsyncSession):
    try:
        default_roles = ["ADMIN", "USER"]

        for role_name in default_roles:
            stmt = select(Role).where(Role.name == role_name, Role.is_deleted == False)
            result = await db.execute(stmt)
            role = result.scalars().first()

            if not role:
                new_role = Role(
                    uuid=str(uuid.uuid4()),
                    name=role_name,
                    is_deleted=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(new_role)
                print(f"Created role: {role_name}")

        await db.commit()

        # Ensure the ADMIN role exists
        stmt = select(Role).where(Role.name == "ADMIN", Role.is_deleted == False)
        result = await db.execute(stmt)
        admin_role = result.scalars().first()

        if not admin_role:
            raise ValueError("ADMIN role is missing. Please initialize roles first.")

        # Check if an admin user already exists
        stmt = select(User).where(User.email == "admin@gmail.com", User.is_deleted == False)
        result = await db.execute(stmt)
        admin_user = result.scalars().first()

        print(f"Admin user found: {admin_user}")

        if not admin_user:
            admin_user = User(
                uuid=str(uuid.uuid4()),
                username="admin",
                email="admin@gmail.com",
                password=get_password_hash("Admin@123"),
                is_verified=True,
                is_active=True,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)

            admin_user_role = UserRole(
                uuid=str(uuid.uuid4()),
                user_id=admin_user.id,
                role_id=admin_role.id,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(admin_user_role)
            await db.commit()
            print(f"UserRole assigned: {admin_user_role.id}")

    except Exception as e:
        print(f"Error initializing roles and admin user: {e}")
        await db.rollback()


# Function to create static users
async def create_static_users_batched(db: AsyncSession, num_users: int = 100, batch_size: int = 100):
    try:
        stmt = select(Role).where(Role.name == "USER", Role.is_deleted == False)
        result = await db.execute(stmt)
        user_role = result.scalars().first()

        if not user_role:
            raise ValueError("USER role is missing. Please initialize roles first.")

        users = []
        user_roles = []

        for i in range(num_users):
            fake_name = fake.name()[:100]
            fake_email = fake.email()[:255]
            fake_avatar = fake.image_url()[:255]
            fake_address = fake.address()[:255]
            fake_phone = fake.phone_number()[:20]
            fake_bio = fake.text()[:500]
            fake_gender = fake.random_element(["Male", "Female"])
            fake_dob = fake.date_of_birth()

            user = User(
                uuid=str(uuid.uuid4()),
                username=fake_name,
                email=fake_email,
                password=get_password_hash("Password123"),
                avatar=fake_avatar,
                address=fake_address,
                phone_number=fake_phone,
                bio=fake_bio,
                gender=fake_gender,
                date_of_birth=fake_dob,
                is_verified=True,
                is_active=True,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            users.append(user)

            if len(users) == batch_size:
                db.add_all(users)
                await db.commit()

                for user in users:
                    user_role_entry = UserRole(
                        uuid=str(uuid.uuid4()),
                        user_id=user.id,
                        role_id=user_role.id,
                        is_deleted=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    user_roles.append(user_role_entry)

                db.add_all(user_roles)
                await db.commit()

                users.clear()
                user_roles.clear()

        if users:
            db.add_all(users)
            await db.commit()

            for user in users:
                user_role_entry = UserRole(
                    uuid=str(uuid.uuid4()),
                    user_id=user.id,
                    role_id=user_role.id,
                    is_deleted=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                user_roles.append(user_role_entry)

            db.add_all(user_roles)
            await db.commit()

        print(f"Successfully created {num_users} static users in batches of {batch_size}.")

    except Exception as e:
        print(f"Error creating static users: {e}")
        await db.rollback()
