# Permanent User Order Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a company-level persistent sort order for workers, allowing managers to reorder workers in daily-reports and users pages, which then applies globally across all manager views.

**Architecture:** We will add a `sort_order` column to `CompanyMember`, default to 1000 so new members appear at the bottom. A new API endpoint will update this order in bulk. The frontend will perform optimistic updates and trigger a debounced API call to persist the order.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, React, Next.js

**Execution Mode Recommendation:** Driven (Sequential) - Changes require modifying the database schema and adding endpoints before updating the frontend, making sequential execution optimal.

## Global Constraints

- Code must use standard TypeScript / React / Next.js practices.
- Python backend must use standard FastAPI / SQLAlchemy practices.
- All file paths must be absolute relative to project root.

---

### Task 1: Database and Models Update

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/crud.py`
- Create: backend migration (via terminal)

**Interfaces:**
- Produces: `CompanyMember` model now has `sort_order` column.
- Produces: `crud.get_company_members` sorts by `sort_order` ASC, `joined_at` ASC.

**Implementation Steps:**
- [ ] **Step 1: Update the CompanyMember Model** - In `backend/models.py`, add `sort_order = Column(Integer, default=1000, server_default="1000")` to `CompanyMember` class.
- [ ] **Step 2: Generate Alembic Migration** - Run `docker compose -f docker-compose.dev.yml exec backend alembic revision --autogenerate -m "add sort_order to company_members"`. Then run `docker compose -f docker-compose.dev.yml exec backend alembic upgrade head`.
- [ ] **Step 3: Update crud.py sorting** - In `backend/crud.py`, modify `get_company_members` to order the query by `models.CompanyMember.sort_order.asc()` and `models.CompanyMember.joined_at.asc()`.
- [ ] **Step 4: Commit** - ```bash
git add backend/models.py backend/crud.py backend/migrations/versions/
git commit -m "feat: add sort_order to CompanyMember and update fetching"
```

### Task 2: Update Members Order Endpoint

**Files:**
- Modify: `backend/schemas.py`
- Modify: `backend/routers/companies.py`
- Modify: `backend/crud.py`

**Interfaces:**
- Consumes: The `CompanyMember` model.
- Produces: `PUT /companies/{company_id}/members/order` endpoint.

**Implementation Steps:**
- [ ] **Step 1: Add Pydantic schemas** - In `backend/schemas.py`, add `UpdateCompanyMembersOrder(BaseModel)` containing `user_ids: List[str]`.
- [ ] **Step 2: Add CRUD function** - In `backend/crud.py`, add `update_company_members_order(db: Session, company_id: str, user_ids: List[str])`. It should loop over `user_ids` with `enumerate`, fetch each corresponding `CompanyMember` for the given `company_id`, and update its `sort_order` to the index. Commit changes to DB.
- [ ] **Step 3: Add API route** - In `backend/routers/companies.py`, add a `PUT` endpoint `/companies/{company_id}/members/order` that calls `update_company_members_order`. Make sure to enforce manager permissions.
- [ ] **Step 4: Commit** - ```bash
git add backend/schemas.py backend/routers/companies.py backend/crud.py
git commit -m "feat: add endpoint to update company members order"
```

### Task 3: Frontend API Integration

**Files:**
- Modify: `frontend/src/lib/api/companies.ts`

**Interfaces:**
- Consumes: `PUT /companies/{company_id}/members/order` endpoint.
- Produces: `updateCompanyMembersOrder` function in `companies.ts`.

**Implementation Steps:**
- [ ] **Step 1: Add update function** - In `frontend/src/lib/api/companies.ts`, implement `updateCompanyMembersOrder(companyId: string, userIds: string[])`. It should make a PUT request to `/companies/${companyId}/members/order` with the body `{ user_ids: userIds }`.
- [ ] **Step 2: Commit** - ```bash
git add frontend/src/lib/api/companies.ts
git commit -m "feat: add updateCompanyMembersOrder api call"
```

### Task 4: Frontend Daily Reports Page

**Files:**
- Modify: `frontend/src/app/(app)/manager/daily-reports/page.tsx`

**Interfaces:**
- Consumes: `updateCompanyMembersOrder` from API.
- Produces: Persisted order state instead of local-only sorting override.

**Implementation Steps:**
- [ ] **Step 1: Remove local sorting overrides** - Remove the custom `list.sort()` logic related to manager/active groups inside `sortedUsers` memo. Instead, just use the order provided by `companyUsers`, as the backend handles sorting.
- [ ] **Step 2: Update moveUser logic** - When `moveUser` is called (Up/Down arrow), swap the elements in the local array (which could be managed via React state like `localUsers` initialized from `companyUsers`). Do an optimistic update so the UI reacts immediately.
- [ ] **Step 3: Add API call on move** - Call `updateCompanyMembersOrder` asynchronously when the order changes. You may use a simple timeout or direct call. Ensure the `userOrder` state logic is replaced by the persisted `localUsers` order.
- [ ] **Step 4: Commit** - ```bash
git add frontend/src/app/(app)/manager/daily-reports/page.tsx
git commit -m "feat: persist user order in daily reports"
```

### Task 5: Frontend Users Page

**Files:**
- Modify: `frontend/src/app/(app)/manager/users/page.tsx`

**Interfaces:**
- Consumes: `updateCompanyMembersOrder` from API.
- Produces: Arrows and sorting logic in manager's user list page.

**Implementation Steps:**
- [ ] **Step 1: Apply backend sorting** - Ensure the users list renders in the order returned from the backend (which is sorted by `sort_order`).
- [ ] **Step 2: Add Up/Down arrows** - If not present, add Up/Down arrows (like in `daily-reports`) next to each user's name or actions.
- [ ] **Step 3: Implement move logic** - Implement the same optimistic move and API update logic used in `daily-reports`.
- [ ] **Step 4: Commit** - ```bash
git add frontend/src/app/(app)/manager/users/page.tsx
git commit -m "feat: add sort ordering to manager users page"
```
