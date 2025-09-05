# Templates Folder

This folder contains template files for various tax forms and reports.

## 📄 **Available Templates**

### FA_Declaration_Template.csv
**Purpose**: Template for Foreign Assets (FA) declaration forms
**Description**: Contains the standard column headers required for FA declaration CSV imports

**Column Structure:**
- Country/Region name
- Country Name and Code  
- Name of entity
- Address of entity
- ZIP Code
- Nature of entity
- Date of acquiring the interest
- Initial value of the investment
- Peak value of investment during the Period
- Closing balance
- Total gross amount paid/credited with respect to the holding during the period
- Total gross proceeds from sale or redemption of investment during the period

**Usage**: This template is used by the FA CSV export functionality to ensure proper column ordering and formatting for tax software imports.

## 🔧 **How Templates Are Used**

The application automatically reads these template files to:
1. **Determine Column Structure**: Uses template headers to format exported CSV files
2. **Ensure Compatibility**: Maintains format compatibility with tax filing software
3. **Validate Export Format**: Ensures all required columns are included in exports

## 📝 **Adding Custom Templates**

To add custom templates:
1. Place CSV template file in this directory
2. Update application configuration to reference the new template
3. Use consistent naming convention: `[ReportType]_Template.csv`

## 🎯 **Benefits**

- **Consistency**: Ensures all exports use standardized formats
- **Flexibility**: Easy to update templates without code changes
- **Compliance**: Templates match official tax form requirements
- **Reusability**: Templates can be used across different tax years
