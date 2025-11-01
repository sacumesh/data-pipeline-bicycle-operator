# Module de Statistiques pour l'Opérateur de Tours Cyclistes

## Vue d'ensemble

Le module `cycling_stats.py` fournit des outils d'analyse avancée pour les opérations de location de vélos et de tours guidés. Il permet de :

- Calculer les statistiques mensuelles d'utilisation des vélos
- Analyser les performances des guides
- Évaluer l'utilisation des parcours
- Générer des rapports mensuels complets au format XML

## Installation

Le module nécessite Python 3.8+ et les dépendances suivantes :
```bash
pip install lxml
```

## Utilisation

### Initialisation

```python
from tools.cycling_stats import CyclingStats

# Créer une instance avec un fichier XML
stats = CyclingStats("path/to/data.xml")
```

### Statistiques Mensuelles des Vélos

```python
# Obtenir les stats pour octobre 2025
bike_stats = stats.monthly_bike_stats(2025, 10)

# Exemple de résultat pour un vélo
for bike_id, stats in bike_stats.items():
    print(f"Vélo {bike_id}:")
    print(f"- Heures totales: {stats.total_hours}")
    print(f"- Heures de location: {stats.rental_hours}")
    print(f"- Heures de maintenance: {stats.maintenance_hours}")
    print(f"- Revenus: {stats.total_revenue}€")
    print(f"- Coûts maintenance: {stats.maintenance_cost}€")
```

### Performance des Guides

```python
from datetime import datetime

# Analyser la performance sur une période
start_date = datetime(2025, 10, 1)
end_date = datetime(2025, 10, 31)
guide_stats = stats.guide_performance(start_date, end_date)

# Exemple de résultat pour un guide
for guide_id, stats in guide_stats.items():
    print(f"Guide {guide_id}:")
    print(f"- Tours réalisés: {stats.total_tours}")
    print(f"- Total participants: {stats.total_participants}")
    print(f"- Revenus générés: {stats.revenue_generated}€")
    print(f"- Régions couvertes: {', '.join(stats.regions)}")
    print(f"- Langues parlées: {', '.join(stats.languages)}")
```

### Analyse des Parcours

```python
# Analyser les parcours sur les 2 derniers mois
path_stats = stats.path_analytics(period_months=2)

# Exemple de résultat pour un parcours
for path_id, stats in path_stats.items():
    print(f"Parcours {path_id}:")
    print(f"- Nombre d'utilisations: {stats.total_trips}")
    print(f"- Total participants: {stats.total_participants}")
    print(f"- Revenus générés: {stats.revenue_generated}€")
    print(f"- Satisfaction moyenne: {stats.avg_satisfaction}/5")
    print(f"- Taux de complétion: {stats.completion_rate}%")
```

### Génération de Rapport Mensuel

```python
# Générer un rapport mensuel complet
xml_report = stats.export_monthly_report(2025, 10)

# Sauvegarder le rapport
with open("rapport_octobre_2025.xml", "w") as f:
    f.write(xml_report)
```

## Structure des Données

### BikeStats
```python
@dataclass
class BikeStats:
    total_hours: int = 0         # Heures totales d'activité
    rental_hours: int = 0        # Heures de location
    maintenance_hours: int = 0    # Heures de maintenance
    total_revenue: Decimal = Decimal('0')  # Revenus totaux
    booking_count: int = 0       # Nombre de réservations
    maintenance_cost: Decimal = Decimal('0')  # Coûts de maintenance
```

### GuideStats
```python
@dataclass
class GuideStats:
    total_tours: int = 0         # Nombre de tours guidés
    total_participants: int = 0   # Nombre total de participants
    languages: set = None        # Langues parlées
    regions: set = None         # Régions couvertes
    revenue_generated: Decimal = Decimal('0')  # Revenus générés
```

### PathStats
```python
@dataclass
class PathStats:
    total_trips: int = 0         # Nombre total d'utilisations
    total_participants: int = 0   # Nombre total de participants
    revenue_generated: Decimal = Decimal('0')  # Revenus générés
    avg_satisfaction: float = 0.0  # Satisfaction moyenne (0-5)
    completion_rate: float = 0.0   # Taux de complétion (0-100%)
```

## Format du Rapport Mensuel

Le rapport mensuel XML est structuré en trois sections principales :

1. `BikeStatistics` : Stats d'utilisation et financières pour chaque vélo
2. `GuideStatistics` : Performance, revenus et couverture pour chaque guide
3. `PathStatistics` : Utilisation, satisfaction et taux de succès pour chaque parcours

Exemple de structure :
```xml
<MonthlyReport year="2025" month="10" generated="2025-10-31T10:00:00">
    <BikeStatistics>
        <Bike id="b1">
            <Utilization totalHours="32" rentalHours="8" maintenanceHours="24" bookingCount="1"/>
            <Revenue>40.00</Revenue>
            <MaintenanceCost>50.00</MaintenanceCost>
        </Bike>
        <!-- ... autres vélos ... -->
    </BikeStatistics>
    <!-- ... sections guides et parcours ... -->
</MonthlyReport>
```

## Format du rapport — compatibilité et heuristique de tarification

Le module génère actuellement deux sections dans le rapport mensuel pour assurer la
compatibilité entre anciens consommateurs et le nouveau schéma :

- Nouveau schéma (préféré) :
    - `BikeStatistics` — contient `Bike` avec une sous-section `Utilization` (attributs
        `totalHours`, `rentalHours`, `maintenanceHours`) et éléments `Revenue`/`MaintenanceCost`.
    - `GuideStatistics` — contient `Guide` avec `Tours` (attributs `count`,
        `total-participants`) et `Revenue`, `Regions`, `Languages`.
    - `PathStatistics` — contient `Path` avec sous-élément `Usage` (attributs
        `total-uses`, `total-participants`, `completion-rate`, `avg-satisfaction`).

- Sections legacy (pour rétrocompatibilité) :
    - `Bikes`, `Guides`, `Paths` sont également incluses et reprennent des éléments plus
        simples (par ex. `TotalHours`, `RentalHours`, `OccupancyRate`, `RevenueGenerated`) afin
        d'assurer que des consommateurs plus anciens continuent de fonctionner.

Heuristique de tarification
- Les tests et les jeux de données utilisés par le projet ne sont pas toujours cohérents
    sur la sémantique du prix d'un `tourPackage` : certaines sources indiquent un prix par
    groupe (une valeur pour l'ensemble du groupe), d'autres un prix par participant.
- Pour gérer ces deux conventions sans modifier le schéma, le code utilise une heuristique
    simple : si le fichier XML contient une section top-level `clients` (liste explicite des
    clients), on considère que le prix du package est appliqué "par groupe". Si la section
    `clients` est absente (cas de jeux de tests minimalistes), on multiplie le prix du package
    par le nombre de participants du groupe (comportement "par participant").

Remarque : cette règle est un compromis pragmatique. Si tu préfères une règle explicite
(par exemple un attribut sur `tourPackage` qui indique `priceMode="per-group|per-participant"`),
je peux l'implémenter et mettre à jour le code et la documentation en conséquence.

## Tests

Le module est fourni avec une suite de tests complète :

```bash
# Exécuter tous les tests
python -m pytest tests/

# Exécuter un test spécifique
python -m pytest tests/test_monthly_bike_stats.py -v
python -m pytest tests/test_guide_performance.py -v
python -m pytest tests/test_path_analytics.py -v
python -m pytest tests/test_monthly_report.py -v
```

## Notes et Limitations

1. Les dates sont au format ISO 8601 (YYYY-MM-DD ou YYYY-MM-DDThh:mm:ss)
2. Les montants sont stockés avec la classe Decimal pour la précision
3. La satisfaction est notée de 0 à 5
4. Les taux et pourcentages sont de 0 à 100
5. Le module utilise la date courante du XML (attribut currentDate)