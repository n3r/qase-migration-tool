# qase-testit-migration

This script helps you to migrate your test cases from TestIT to Qase. It's written in Python 3.11 and uses [Qase API](https://qase.io/api/v1/) and [TestIT API](https://github.com/testit-tms/api-client-python).

## How to use

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

Create a new config file from the example or use template:

```json
{
    "qase": {
        "api_token": "<QASE_API_TOKEN>",
        "host": "<QASE_API_HOST|Default:qase.io>",
        "ssl": true,
        "enterprise": false
    },
    "testit": {
        "host": "<TESTIT_HOST>",
        "token": "<TESTIT_TOKEN>",
    }
}
```

Required fields to fill:

- `qase.host` - Qase host
- `qase.api` - API token from Qase
- `qase.scim` - SCIM token from Qase
- `qase.ssl` - If set to `true` migrator will use `https` instead of `http` in all requests
- `testit.host` - URL of your TestIT instance
- `testit.token` - TestIT API token

### 3. Run

```bash
python start.py
```
