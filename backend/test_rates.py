from database import SessionLocal
from models import Company, CompanyMember

db = SessionLocal()
companies = db.query(Company).all()
for c in companies:
    members = db.query(CompanyMember).filter(CompanyMember.company_id == c.id).all()
    if members:
        print(f"Company: {c.name}")
        for m in members:
            print(f"  User: {m.user.email}, RatesConfig: {m.rates_config}")
