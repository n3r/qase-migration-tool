# Qase Zephyr Enterprise Migration Tool

This script helps you to migrate your test cases from Zephyr Enterprise to Qase. It's written in Python 3.11 and uses [Qase API](https://qase.io/api/v1/) and [Zephyr Enterprise API](https://zephyrenterprisev3.docs.apiary.io/).

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
    "zephyr_enterprise": {
        "api": {
            "host": "<ZEPHYR_ENTERPRISE_API_HOST>",
            "token": "<ZEPHYR_ENTERPRISE_API_TOKEN>",
        }
    },
    "projects": {
        "import": [],
        "status": "all|active|archived"
    },
}
```

Required fields to fill:

- `qase.host` - Qase host
- `qase.api` - API token from Qase
- `qase.scim` - SCIM token from Qase
- `qase.ssl` - If set to `true` migrator will use `https` instead of `http` in all requests
- `zephyr_enterprise.host` - URL of your Zephyr Enterprise instance
- `zephyr_enterprise.token` - Zephyr Enterprise API token

Or you can copy the example config file from `examples/zephyr_enterprise.config.json` and fill it with your data.

### 3. Run

```bash
python start.py
```
