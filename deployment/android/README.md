# CareQFlow Android client

This Android module is a native WebView client for a CareQFlow host.

The Android device does not run the CareQFlow Python backend or SQLCipher database.
It connects over HTTPS to the CareQFlow host, which remains the single source of
truth for application data, authentication, audit logging, backups, and database
encryption.

## Default server

The default server URL is:

`https://careqflow.local/`

The server can be changed from the app's **Server** menu.

Only HTTPS server URLs are accepted. Cleartext HTTP is disabled by Android's
network security configuration.

## Private CA support

CareQFlow's Linux deployment currently uses Caddy `tls internal`. Android does not
trust user-installed certificate authorities by default for modern target SDKs, so
this app's network security configuration explicitly permits both system and
user-installed trust anchors while still requiring HTTPS.

The CareQFlow host CA must be installed and trusted on the Android device before
the app can connect to an internal-CA deployment. The app never bypasses TLS
certificate errors.

## Build

From the repository root:

```powershell
.\deployment\android\gradlew.bat -p .\deployment\android testDebugUnitTest
.\deployment\android\gradlew.bat -p .\deployment\android assembleDebug
```

The debug APK is generated at:

`deployment\android\app\build\outputs\apk\debug\app-debug.apk`

## Scope

This Android client deliberately does not contain:

- Python or FastAPI
- SQLCipher database files
- CareQFlow backend services
- Caddy
- Termux or a Linux userspace
- an embedded production copy of the React frontend

The CareQFlow host serves the current frontend and API so Android clients stay in
sync with the deployed server version.
