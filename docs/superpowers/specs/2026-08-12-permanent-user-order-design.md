# Design Specification: Permanent User Order

## Context
Currently, the daily reports page allows managers to reorder workers using up/down arrows, but this order is only saved locally in the frontend state. The goal is to make this custom sorting order permanent at the company level. Once modified, this order should be reflected across all tables where users are listed (e.g., Billing, Daily Reports, Users list) when viewed by a manager of that company.

## Requirements
- **Company-level Persistence**: The custom order must be saved to the database and shared among all managers of the same company.
- **Global Application**: The saved order must dictate the display order of users across all relevant pages (Daily Reports, Billing, Users list, etc.).
- **Absolute Override**: The custom order completely overrides the default grouping behavior (which previously grouped by active/inactive and manager/worker). Managers can freely mix user types.
- **New User Handling**: Newly joined users must automatically appear at the **bottom** of the custom order until manually moved.
- **Modification Points**: The up/down arrows to modify the order will be present on specific management pages (Daily Reports and Users List). Other pages (like Billing) will simply display the list in the fixed order without offering the arrows.

## Architecture & Implementation

### 1. Database (Backend)
- Add a new column `sort_order` (Integer) to the `company_members` table.
- **Default Value**: Set a high default value (e.g., `1000`) for `sort_order` so that new members are appended to the bottom of the list without requiring a query for the current max value.
- **Sorting on Fetch**: Update the `read_companies_detailed` (or wherever company members are fetched) to sort the relationships by `sort_order ASC, joined_at ASC`.

### 2. API Endpoint
- Create a new endpoint: `PUT /companies/{company_id}/members/order`
- **Payload**: Accepts a list of `user_id`s representing the new desired order. Example: `{"user_ids": ["uuid-1", "uuid-2", ...]}`
- **Logic**: Performs a bulk update on the `company_members` table, setting the `sort_order` to the index of the `user_id` in the array (0, 1, 2, ...).

### 3. Frontend Implementation
- **State Management**: The API response for company members will already be sorted by the backend. The frontend should rely on this order.
- **Daily Reports Page (`manager/daily-reports/page.tsx`)**:
  - Remove the local `userOrder` state that was overriding the sorting.
  - Implement a `moveUser` function that performs an optimistic update on the local array (swapping positions).
  - After the optimistic update, trigger a debounced API call to `PUT /companies/{company_id}/members/order` with the new array of IDs.
- **Users Page (`manager/users/page.tsx` or equivalent)**:
  - Add the same up/down arrow UI and `moveUser` logic if it doesn't already exist.
- **Other Pages (e.g., Billing)**:
  - Simply map over the users as returned by the API. They will naturally appear in the custom order.

## Trade-offs & Considerations
- **Optimistic UI**: Implementing optimistic updates ensures the UI feels snappy when clicking arrows multiple times rapidly, hiding the latency of the API call.
- **Debouncing**: Rapid clicks on the arrows could spam the API. A simple debounce or sending the update when the user stops clicking for a moment (or just letting the optimistic UI handle rapid state changes while the API catches up in the background) is recommended.
- **Concurrency**: If two managers reorder simultaneously, the last request wins. Given the scale, this is an acceptable trade-off.

## Spec Self-Review Check
- [x] Placeholder scan: No vague requirements or TBDs.
- [x] Internal consistency: The frontend relies on the backend sorting, which aligns with the new column and endpoint.
- [x] Scope check: Focused strictly on persisting user order.
- [x] Ambiguity check: Clarified that new users go to the bottom by defaulting `sort_order` to 1000.
