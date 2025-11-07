# data-pipeline-bicycle-operator
## Sofiane Chaoui

### Step 1 ✅
- **Define the structure with drawio, create a diagram XSD**
  - destination
  - bikes
  - guides
  - clients
  - packages
  - bookings
- ** model.drawio & create model.xsd
### Step 2 ✅
- **With sample.xml create data**
### Step 3 🔄
- **Scenarios XSLT HTML generate HTML pages**
### Step 4 ❌
- **Exports XML and JSON**
### Step 5 ❌
- **Test and finalization**


# start verification of sample.xml and model.xsd
```
python python/run.py --xml data/sample.xml --xsd schema/model.xsd --validate
```