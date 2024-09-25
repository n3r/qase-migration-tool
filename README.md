# qase-migration-tool

This tool helps you to migrate your test cases from various test management tools to Qase. It's written in Python 3.11 and uses [Qase API](https://qase.io/api/v1/) to migrate the following data:

- Test cases
- Test runs
- Test configurations
- Test suites
- Test attachments

The set of data that can be migrated depends on the test management tool used. For more information, refer to the documentation for each tool.

## How to use

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

Follow the instructions for your chosen test management tool to configure the connection details:

- [TestRail](docs/testrail.md)
- [TestIt](docs/testit.md)
- [Zephyr Enterprise](docs/zephyr_enterprise.md)

### 3. Run

```bash
python start.py
```
