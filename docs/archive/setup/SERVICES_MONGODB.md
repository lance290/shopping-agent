# MongoDB (Atlas) Setup

MongoDB works well for schemaless data and fast iteration. This guide uses
MongoDB Atlas because it has a generous free tier and requires minimal setup.

---

## 1. Create an Atlas Cluster

1. Sign in at <https://cloud.mongodb.com>.
2. **Build a Database** → Choose the *Shared* tier (M0) to start.
3. Select a region close to your users (ensure it matches your Cloud Run region
   if latency matters).
4. Leave default settings and deploy.

---

## 2. Configure Access

### Database User

1. In **Database Access**, add a new database user.
2. Use a descriptive username (e.g., `mvp-app`) and a strong password.
3. Assign the `Atlas admin` role during prototyping; scope down later.

### Network Access

1. In **Network Access**, click **Add IP Address**.
2. Allow your development IP (or `0.0.0.0/0` temporarily while iterating).
3. Add Cloud Run's egress IP once you know it, or use VPC peering for private access.

---

## 3. Connection String

From the **Database** view, click **Connect** → **Drivers** → choose Node.js.
Copy the URI and set it in `.env`:

```bash
MONGODB_URI=mongodb+srv://mvp-app:<password>@cluster0.xxxxx.mongodb.net/mvp?retryWrites=true&w=majority
```

Replace `<password>` with the credential you created earlier. You can append
additional query parameters (e.g., TLS options) as needed.

---

## 4. Local Tooling

Install the MongoDB CLI for quick introspection:

```bash
brew tap mongodb/brew
brew install mongodb-atlas
# or: curl -s https://install.mongodb.com/atlascli | sh
```

Now you can run:

```bash
mongosh "$MONGODB_URI"
```

---

## 5. Production Considerations

- Configure a separate database (e.g., `mvp_test`) for automated tests.
- Enable database access restrictions and IP allowlists before going live.
- Set up backups (Atlas automatic snapshots) and alerting.

---

## 6. Secrets & CI

Store the connection URI in a secret manager (`SECRETS_MANAGEMENT.md`) and add a
GitHub secret (e.g., `MONGODB_URI`) if your CI needs to access MongoDB.

Document the chosen database in `.cfoi/branches/<branch>/DECISIONS.md` so future
developers know why and how it was configured.

