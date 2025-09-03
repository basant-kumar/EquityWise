# 🏦 Bank Statement Patterns Configuration

EquityWise automatically parses USD remittance details from bank statement transaction remarks to reconcile RSU proceeds. Different banks use different formats for transaction descriptions, so you can configure custom patterns to match your bank's format.

## 📋 **Current Supported Banks**

| Bank | Pattern | Example Transaction |
|------|---------|---------------------|
| **SBI** (Default) | `IRM/USD([\d.]+)@([\d.]+)GST([\d.]+)` | `IRM/USD6213.87@87.0375GST576/INREM/20250204115415` |
| **HDFC** | `USD\s+([\d.]+)\s+@\s+([\d.]+)\s+GST\s+([\d.]+)` | `USD 6213.87 @ 87.0375 GST 576 REMITTANCE RECEIVED` |
| **ICICI** | `USD([\d.]+)/RATE([\d.]+)/GST([\d.]+)` | `USD6213.87/RATE87.0375/GST576` |
| **Axis** | `FOREX\s+USD([\d.]+)\s+RATE([\d.]+)\s+SERVICE([\d.]+)` | `FOREX USD6213.87 RATE87.0375 SERVICE576` |
| **Kotak** | `REMIT\s+USD([\d.]+)\s+EXRATE([\d.]+)\s+CHARGES([\d.]+)` | `REMIT USD6213.87 EXRATE87.0375 CHARGES576` |

## 🎯 **Pattern Requirements**

Each pattern must capture exactly **3 groups** in order:
1. **USD Amount**: The USD amount received (e.g., `6213.87`)
2. **Exchange Rate**: The USD to INR rate used (e.g., `87.0375`)
3. **Charges/GST**: Service charges or GST deducted (e.g., `576`)

## 🔧 **Configuration Methods**

### Method 1: Environment Variables

Set your default bank pattern:
```bash
export RSU_FA_DEFAULT_BANK_PATTERN="hdfc"
```

Add custom patterns via JSON:
```bash
export RSU_FA_BANK_REMITTANCE_PATTERNS='{"mybank": "USD\\s+([\\d.]+)\\s+RATE([\\d.]+)\\s+FEE([\\d.]+)"}'
```

### Method 2: Configuration File

Create `config/settings.toml`:
```toml
[bank_settings]
default_bank_pattern = "hdfc"

[bank_settings.bank_remittance_patterns]
mybank = "USD\\s+([\\d.]+)\\s+RATE([\\d.]+)\\s+FEE([\\d.]+)"
unionbank = "FOREX\\s+([\\d.]+)USD\\s+@([\\d.]+)\\s+CHARGES([\\d.]+)"
```

### Method 3: Programmatic Configuration

```python
from equitywise.config.settings import settings

# Add a custom pattern
success = settings.add_bank_pattern(
    bank_name="mybank",
    pattern=r"USD\s+([^d.]+)\s+RATE([^d.]+)\s+FEE([^d.]+)",
    set_as_default=True
)

# Test the pattern
test_result = settings.test_bank_pattern(
    pattern=r"USD\s+([^d.]+)\s+RATE([^d.]+)\s+FEE([^d.]+)",
    test_string="USD 6213.87 RATE87.0375 FEE576 WIRE TRANSFER"
)

if test_result:
    print(f"USD: {test_result['usd_amount']}")
    print(f"Rate: {test_result['exchange_rate']}")
    print(f"Fee: {test_result['charges_gst']}")
```

## 🧪 **Testing Your Pattern**

### Step 1: Find a Sample Transaction

Look for a USD remittance entry in your bank statement, for example:
```
WIRE TRANSFER USD 5000.50 RATE 82.4567 SERVICE CHARGE 450 REF:ABC123
```

### Step 2: Create Pattern

Create a regex pattern that captures the three required groups:
```regex
USD\s+([^d.]+)\s+RATE\s+([^d.]+)\s+SERVICE\s+CHARGE\s+([^d.]+)
```

### Step 3: Test Pattern

```bash
uv run python -c "
from equitywise.config.settings import settings

# Test your pattern
pattern = r'USD\s+([^d.]+)\s+RATE\s+([^d.]+)\s+SERVICE\s+CHARGE\s+([^d.]+)'
sample = 'WIRE TRANSFER USD 5000.50 RATE 82.4567 SERVICE CHARGE 450 REF:ABC123'

result = settings.test_bank_pattern(pattern, sample)
if result:
    print('✅ Pattern works!')
    print(f'USD: {result[\"usd_amount\"]}')
    print(f'Rate: {result[\"exchange_rate\"]}') 
    print(f'Charges: {result[\"charges_gst\"]}')
else:
    print('❌ Pattern does not match')
"
```

### Step 4: Add to Configuration

```bash
uv run python -c "
from equitywise.config.settings import settings

# Add your custom pattern
settings.add_bank_pattern(
    bank_name='mybank', 
    pattern=r'USD\s+([^d.]+)\s+RATE\s+([^d.]+)\s+SERVICE\s+CHARGE\s+([^d.]+)',
    set_as_default=True
)

print('✅ Custom bank pattern added!')
"
```

## 🔍 **Common Pattern Examples**

### Space-Separated Format
```regex
USD\s+([^d.]+)\s+@\s+([^d.]+)\s+GST\s+([^d.]+)
```
Matches: `USD 6213.87 @ 87.0375 GST 576`

### Slash-Separated Format  
```regex
USD([^d.]+)/RATE([^d.]+)/GST([^d.]+)
```
Matches: `USD6213.87/RATE87.0375/GST576`

### Keyword-Based Format
```regex
FOREX\s+USD([^d.]+)\s+RATE([^d.]+)\s+SERVICE([^d.]+)
```
Matches: `FOREX USD6213.87 RATE87.0375 SERVICE576`

### Mixed Format with Extra Text
```regex
.*USD\s+([^d.]+).*@([^d.]+).*CHARGES?\s+([^d.]+)
```
Matches: `INTERNATIONAL WIRE USD 6213.87 RECEIVED @87.0375 CHARGES 576 REF:XYZ789`

## ❓ **Troubleshooting**

### Pattern Not Matching

1. **Check Groups**: Ensure exactly 3 capture groups `(...)` 
2. **Test Incrementally**: Start simple, add complexity
3. **Escape Special Characters**: Use `\\` for literal dots, slashes
4. **Use Online Regex Tester**: Test at https://regex101.com

### Common Issues

- **Too Few Groups**: Pattern needs exactly 3 groups
- **Wrong Group Order**: Must be (USD, Rate, Charges) 
- **Case Sensitivity**: Patterns are case-sensitive
- **Whitespace**: Use `\s+` for variable spacing

### Debug Mode

Run with debug logging to see pattern matching:
```bash
uv run equitywise --log-level DEBUG calculate-rsu --financial-year FY24-25
```

## 📞 **Getting Help**

If you're having trouble creating a pattern for your bank:

1. **Share Sample**: Provide a sample transaction (with sensitive data masked)
2. **Open Issue**: Create a GitHub issue with your bank name and sample
3. **Community**: Ask in discussions for pattern help

Example request:
```
Bank: ABC Bank
Sample: "WIRE TXN USD XXXX.XX RATE XX.XXXX SERVICE XX REF:XXXXXX"  
Need help creating pattern for this format
```

---

**💡 Pro Tip**: Once you have a working pattern, share it with the community by submitting a pull request to add it to the default patterns!
