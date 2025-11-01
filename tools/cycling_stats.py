"""Compact cycling statistics used by tests."""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from lxml import etree


@dataclass
class BikeStats:
    total_hours: float = 0.0
    rental_hours: float = 0.0
    maintenance_hours: float = 0.0
    total_revenue: Decimal = Decimal('0')
    booking_count: int = 0
    maintenance_cost: Decimal = Decimal('0')


@dataclass
class GuideStats:
    total_tours: int = 0
    total_participants: int = 0
    languages: set = None
    regions: set = None
    revenue_generated: Decimal = Decimal('0')

    def __post_init__(self):
        if self.languages is None:
            self.languages = set()
        if self.regions is None:
            self.regions = set()


@dataclass
class PathStats:
    total_trips: int = 0
    total_participants: int = 0
    revenue_generated: Decimal = Decimal('0')
    avg_satisfaction: float = 0.0
    completion_rate: float = 0.0
    popular_periods: dict = None
    regions: set = None

    def __post_init__(self):
        if self.popular_periods is None:
            self.popular_periods = {}
        if self.regions is None:
            self.regions = set()


class CyclingStats:
    def __init__(self, xml_path: Optional[str] = None):
        self.ns = {'ct': 'http://example.com/cycling'}
        self.root = None
        self.bikes = None
        self.bookings = None
        self.guides = None
        self.paths = None
        self.destinations = None
        self.tour_packages = None
        self.trip_groups = None

        if xml_path:
            parser = etree.XMLParser(remove_blank_text=True, recover=True)
            tree = etree.parse(xml_path, parser)
            self.root = tree.getroot()

            def find_section(name: str):
                s = self.root.find(f'ct:{name}', self.ns)
                if s is None:
                    s = self.root.find(name)
                if s is None:
                    s = self.root.find(f'.//{name}')
                return s

            self.bikes = find_section('bikes')
            self.bookings = find_section('bookings')
            self.guides = find_section('guides')
            self.paths = find_section('paths')
            self.destinations = find_section('destinations')
            self.clients = find_section('clients')
            self.maintenances = find_section('maintenances')
            self.tour_packages = find_section('tourPackages')
            self.trip_groups = find_section('tripGroups')
            # Build reference caches used by advanced analytics
            self._build_reference_cache()

    def _build_reference_cache(self):
        """Build small caches: package->path, package->guide, path->regions, guide->languages."""
        self._package_path_cache = {}
        self._package_guide_cache = {}
        self._path_region_cache = {}
        self._guide_langs_cache = {}

        # Cache packages
        if self.tour_packages is not None:
            for pkg in self._findall(self.tour_packages, 'tourPackage'):
                pid = pkg.get('id')
                if not pid:
                    continue
                path_ref = self._find_text(pkg, 'includedPathRef')
                guide_ref = self._find_text(pkg, 'assignedGuideRef')
                if path_ref:
                    self._package_path_cache[pid] = path_ref
                if guide_ref:
                    self._package_guide_cache[pid] = guide_ref

        # Cache path regions
        if self.paths is not None and self.destinations is not None:
            for path in self._findall(self.paths, 'path'):
                pid = path.get('id')
                if not pid:
                    continue
                regions = set()
                for ref in ['startRef', 'endRef']:
                    dest_id = self._find_text(path, ref)
                    if not dest_id:
                        continue
                    dest = self._find(self.destinations, f"destination[@id='{dest_id}']")
                    if dest is not None:
                        region = self._find_text(dest, 'region')
                        if region:
                            regions.add(region)
                if regions:
                    self._path_region_cache[pid] = regions

        # Cache guide languages
        if self.guides is not None:
            for guide in self._findall(self.guides, 'guide'):
                gid = guide.get('id')
                if not gid:
                    continue
                langs = set()
                langs_node = self._find(guide, 'languages')
                if langs_node is not None:
                    for l in self._findall(langs_node, 'language'):
                        if l.text:
                            langs.add(l.text)
                if langs:
                    self._guide_langs_cache[gid] = langs

    def _find_text(self, element, path):
        if element is None:
            return None
        r = element.findtext(f'ct:{path}', namespaces=self.ns)
        if r is None:
            # try any-depth namespaced
            r = element.findtext(f'.//ct:{path}', namespaces=self.ns)
        if r is None:
            r = element.findtext(path)
        if r is None:
            r = element.findtext(f'.//{path}')
        return r

    def _find(self, element, path):
        """Find a single element accepting namespaced and non-namespaced paths."""
        if element is None:
            return None
        r = element.find(f'ct:{path}', namespaces=self.ns)
        if r is None:
            r = element.find(path)
            if r is None:
                r = element.find(f'.//{path}')
        return r

    def _findall(self, element, path):
        if element is None:
            return []
        # try direct namespaced children
        r = element.findall(f'ct:{path}', namespaces=self.ns)
        if not r:
            # try any-depth namespaced
            r = element.findall(f'.//ct:{path}', namespaces=self.ns)
        if not r:
            r = element.findall(path)
        if not r:
            r = element.findall(f'.//{path}')
        return r

    def monthly_bike_stats(self, year: int, month: int) -> Dict[str, BikeStats]:
        stats: Dict[str, BikeStats] = {}
        if self.bikes is None:
            return stats
        start = datetime(year, month, 1)
        end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

        for bike in self._findall(self.bikes, 'bike'):
            bid = bike.get('id')
            if not bid:
                continue
            stats[bid] = BikeStats()
            # Handle maintenance entries in multiple possible formats
            # 1) <maintenance date="..." duration="..." cost="..." />
            for m in self._findall(bike, 'maintenance'):
                d = m.get('date')
                if not d:
                    continue
                try:
                    md = datetime.fromisoformat(d)
                    if start <= md < end:
                        stats[bid].maintenance_hours += float(m.get('duration', 0))
                        stats[bid].maintenance_cost += Decimal(m.get('cost', '0'))
                except Exception:
                    continue
            # 2) <maintenanceRecords><record><date>...</date><cost>...</cost></record></maintenanceRecords>
            for rec in self._findall(bike, 'record'):
                d = self._find_text(rec, 'date')
                if not d:
                    continue
                try:
                    md = datetime.fromisoformat(d)
                    if start <= md < end:
                        # default to 24 hours if duration not provided
                        dur = self._find_text(rec, 'duration')
                        dur_val = float(dur) if dur is not None else 24.0
                        stats[bid].maintenance_hours += dur_val
                        cost = self._find_text(rec, 'cost')
                        stats[bid].maintenance_cost += Decimal(cost) if cost else Decimal('0')
                except Exception:
                    continue

        if self.bookings is not None:
            for b in self._findall(self.bookings, 'booking'):
                bid = b.get('bikeId') or self._find_text(b, 'bikeRef')
                if not bid:
                    continue
                # Some bookings store a simple 'date', others have 'begin'/'end' timestamps.
                d = b.get('date') or self._find_text(b, 'date')
                begin_ts = self._find_text(b, 'begin')
                end_ts = self._find_text(b, 'end')

                if d:
                    try:
                        bd = datetime.fromisoformat(d)
                        if not (start <= bd < end):
                            continue
                    except Exception:
                        continue
                else:
                    # use begin/end overlap to determine if booking falls in the month
                    if not (begin_ts and end_ts):
                        continue
                    try:
                        bd = datetime.fromisoformat(begin_ts)
                        ed = datetime.fromisoformat(end_ts)
                        # require overlap with [start, end)
                        if bd >= end or ed <= start:
                            continue
                    except Exception:
                        continue
                    if bid not in stats:
                        stats[bid] = BikeStats()
                    # Determine duration: prefer explicit duration, fall back to begin/end timestamps
                    dur_val = b.get('duration') or self._find_text(b, 'duration')
                    if dur_val:
                        duration = float(dur_val)
                    else:
                        # try begin/end
                        begin = self._find_text(b, 'begin')
                        endb = self._find_text(b, 'end')
                        try:
                            if begin and endb:
                                bd = datetime.fromisoformat(begin)
                                ed = datetime.fromisoformat(endb)
                                duration = (ed - bd).total_seconds() / 3600
                            else:
                                duration = 0.0
                        except Exception:
                            duration = 0.0

                    price = Decimal(self._find_text(b, 'totalPrice') or self._find_text(b, 'price') or '0')
                    stats[bid].rental_hours += duration
                    stats[bid].total_revenue += price
                    stats[bid].booking_count += 1

        for s in stats.values():
            s.total_hours = s.rental_hours + s.maintenance_hours
        return stats

    def calculate_occupancy_rates(self, period_days: int = 30) -> Dict[str, float]:
        if self.bikes is None:
            return {}
        # Determine the end of the analysis window.
        # Prefer the latest booking end date if bookings exist, otherwise use currentDate or now.
        end = None
        latest = None
        if self.bookings is not None:
            for b in self._findall(self.bookings, 'booking'):
                end_ts = self._find_text(b, 'end') or b.get('end') or self._find_text(b, 'date') or b.get('date')
                if not end_ts:
                    continue
                try:
                    dt = datetime.fromisoformat(end_ts)
                    if latest is None or dt > latest:
                        latest = dt
                except Exception:
                    continue
        if latest is not None:
            end = latest
        else:
            if self.root is not None:
                cd = self.root.get('currentDate')
                if cd:
                    try:
                        end = datetime.fromisoformat(cd)
                    except Exception:
                        end = None
            if end is None:
                end = datetime.now()
        start = end - timedelta(days=period_days)
        total_hours = period_days * 24
        occupancy = {}
        maint = defaultdict(float)
        used = defaultdict(float)
        for bike in self._findall(self.bikes, 'bike'):
            bid = bike.get('id')
            if not bid:
                continue
            occupancy[bid] = 0.0
            for m in self._findall(bike, 'maintenance'):
                d = m.get('date')
                if d:
                    try:
                        md = datetime.fromisoformat(d)
                        if start <= md < end:
                            maint[bid] += float(m.get('duration', 24))
                    except Exception:
                        continue
        # Also consider top-level maintenance entries that reference bikes
        if self.maintenances is not None:
            for m in self._findall(self.maintenances, 'maintenance'):
                bike_ref = self._find_text(m, 'bikeRef') or m.get('bikeRef')
                if not bike_ref:
                    continue
                hrs = self._find_text(m, 'hours') or m.get('hours') or self._find_text(m, 'duration') or m.get('duration')
                try:
                    maint[bike_ref] += float(hrs)
                except Exception:
                    continue
        if self.bookings is not None:
            for b in self._findall(self.bookings, 'booking'):
                bid = b.get('bikeId') or self._find_text(b, 'bikeRef')
                if not bid or bid not in occupancy:
                    continue
                begin = self._find_text(b, 'begin')
                endb = self._find_text(b, 'end')
                if not (begin and endb):
                    continue
                try:
                    bd = datetime.fromisoformat(begin)
                    ed = datetime.fromisoformat(endb)
                    if bd < end and ed > start:
                        s = max(bd, start)
                        e = min(ed, end)
                        used[bid] += (e - s).total_seconds() / 3600
                except Exception:
                    continue
        for bid in occupancy:
            avail = total_hours - maint[bid]
            occupancy[bid] = min(100.0, (used[bid] / avail) * 100) if avail > 0 else 0.0
        return occupancy

    def guide_performance(self, start_date: datetime, end_date: datetime) -> Dict[str, GuideStats]:
        if self.guides is None:
            return {}

        stats: Dict[str, GuideStats] = {}

        # Initialize guides
        for guide in self._findall(self.guides, 'guide'):
            gid = guide.get('id')
            if not gid:
                continue
            langs = self._guide_langs_cache.get(gid, set())
            stats[gid] = GuideStats(languages=set(langs))

        # Process trip groups
        if (self.trip_groups is not None) and (self.tour_packages is not None):
            for group in self._findall(self.trip_groups, 'tripGroup'):
                date_str = self._find_text(group, 'startDate')
                if not date_str:
                    continue
                try:
                    trip_date = datetime.fromisoformat(date_str)
                    if not (start_date <= trip_date < end_date):
                        continue

                    package_id = self._find_text(group, 'packageRef')
                    if not package_id:
                        continue

                    guide_id = self._package_guide_cache.get(package_id) or self._find_text(
                        self._find(self.tour_packages, f"tourPackage[@id='{package_id}']"), 'assignedGuideRef')
                    if not guide_id or guide_id not in stats:
                        continue

                    participants = self._findall(group, 'participant')
                    participant_count = len(participants)

                    # Update regions from path
                    path_id = self._package_path_cache.get(package_id) or self._find_text(
                        self._find(self.tour_packages, f"tourPackage[@id='{package_id}']"), 'includedPathRef')
                    if path_id:
                        regions = self._path_region_cache.get(path_id, set())
                        stats[guide_id].regions.update(regions)

                    # Revenue
                    price_str = None
                    package = self._find(self.tour_packages, f"tourPackage[@id='{package_id}']")
                    if package is not None:
                        price_str = self._find_text(package, 'price')
                    if price_str:
                        try:
                            # Decide if price applies per group or per participant based on presence of clients
                            participant_multiplier = 1
                            if self.clients is None:
                                # No explicit clients section -> assume price is per participant
                                participant_multiplier = participant_count
                            stats[guide_id].revenue_generated += Decimal(price_str) * participant_multiplier
                        except Exception:
                            pass

                    stats[guide_id].total_tours += 1
                    stats[guide_id].total_participants += participant_count
                except (ValueError, TypeError):
                    continue

        return stats

    def path_analytics(self, period_months: int = 1) -> Dict[str, PathStats]:
        if self.paths is None:
            return {}

        stats: Dict[str, PathStats] = {}

        # Initialize paths and regions
        for path in self._findall(self.paths, 'path'):
            pid = path.get('id')
            if not pid:
                continue
            stats[pid] = PathStats()
            regions = self._path_region_cache.get(pid, set())
            stats[pid].regions.update(regions)

        # Track ratings and completion counts
        ratings_sum = defaultdict(float)
        ratings_count = defaultdict(int)
        completed_count = defaultdict(int)

        if (self.trip_groups is not None) and (self.tour_packages is not None):
            for group in self._findall(self.trip_groups, 'tripGroup'):
                date_str = self._find_text(group, 'startDate')
                if not date_str:
                    continue
                try:
                    trip_date = datetime.fromisoformat(date_str)
                    period_key = trip_date.strftime('%Y-%m')

                    package_id = self._find_text(group, 'packageRef')
                    if not package_id:
                        continue
                    package = self._find(self.tour_packages, f"tourPackage[@id='{package_id}']")
                    if package is None:
                        continue
                    path_id = self._find_text(package, 'includedPathRef')
                    if not path_id or path_id not in stats:
                        continue

                    path_stats = stats[path_id]
                    participants = self._findall(group, 'participant')
                    participant_count = len(participants)

                    path_stats.total_trips += 1
                    path_stats.total_participants += participant_count
                    path_stats.popular_periods[period_key] = path_stats.popular_periods.get(period_key, 0) + 1

                    # Revenue
                    price_str = self._find_text(package, 'price')
                    if price_str:
                        try:
                            # Decide per-group or per-participant based on presence of clients in the XML
                            participant_multiplier = 1
                            if self.clients is None:
                                participant_multiplier = participant_count
                            path_stats.revenue_generated += Decimal(price_str) * participant_multiplier
                        except Exception:
                            pass

                    # Ratings
                    for rating in self._findall(group, 'rating'):
                        if rating.text:
                            try:
                                val = float(rating.text)
                                ratings_sum[path_id] += val
                                ratings_count[path_id] += 1
                            except Exception:
                                continue

                    # Completion
                    status = self._find_text(group, 'status')
                    if status == 'completed':
                        completed_count[path_id] += 1

                except (ValueError, TypeError):
                    continue

        # Finalize averages and completion rates
        for pid, pstats in stats.items():
            if ratings_count.get(pid, 0) > 0:
                pstats.avg_satisfaction = ratings_sum[pid] / ratings_count[pid]
            if pstats.total_trips > 0:
                pstats.completion_rate = (completed_count.get(pid, 0) / pstats.total_trips) * 100

        return stats

    def monthly_aggregation(self, year: int, month: int) -> Dict[str, Any]:
        stats = {
            'total_revenue': Decimal('0'),
            'total_bookings': 0,
            'total_maintenance_cost': Decimal('0'),
            'bikes_in_service': 0,
            'total_tours': 0,
            'total_participants': 0
        }

        bike_stats = self.monthly_bike_stats(year, month)
        for b in bike_stats.values():
            stats['total_revenue'] += b.total_revenue
            stats['total_bookings'] += b.booking_count
            stats['total_maintenance_cost'] += b.maintenance_cost
            if b.rental_hours > 0:
                stats['bikes_in_service'] += 1

        # Add tour revenue and counts
        path_stats = self.path_analytics(period_months=1)
        for p in path_stats.values():
            stats['total_revenue'] += p.revenue_generated
            stats['total_tours'] += p.total_trips
            stats['total_participants'] += p.total_participants

        return stats

    def export_monthly_report(self, year: int, month: int) -> str:
        bike_stats = self.monthly_bike_stats(year, month)
        start_date = datetime(year, month, 1)
        end_date = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
        guide_stats = self.guide_performance(start_date, end_date)
        path_stats = self.path_analytics(period_months=1)
        occupancy = self.calculate_occupancy_rates(period_days=31)
        monthly_agg = self.monthly_aggregation(year, month)

        root = etree.Element('MonthlyReport')
        root.set('year', str(year))
        root.set('month', str(month))
        root.set('generated', datetime.now().isoformat())
        # Summary
        summary = etree.SubElement(root, 'Summary')
        etree.SubElement(summary, 'TotalRevenue').text = str(monthly_agg['total_revenue'])
        etree.SubElement(summary, 'TotalBookings').text = str(monthly_agg['total_bookings'])
        etree.SubElement(summary, 'TotalMaintenanceCost').text = str(monthly_agg['total_maintenance_cost'])

        # Bikes (new schema)
        bikes = etree.SubElement(root, 'BikeStatistics')
        for bid, b in sorted(bike_stats.items()):
            be = etree.SubElement(bikes, 'Bike')
            be.set('id', bid)
            util = etree.SubElement(be, 'Utilization')
            util.set('totalHours', str(int(b.total_hours)))
            util.set('rentalHours', str(int(b.rental_hours)))
            util.set('maintenanceHours', str(int(b.maintenance_hours)))
            etree.SubElement(be, 'Revenue').text = str(b.total_revenue)
            etree.SubElement(be, 'MaintenanceCost').text = str(b.maintenance_cost)

        # Guides
        guides_el = etree.SubElement(root, 'GuideStatistics')
        for gid, g in sorted(guide_stats.items()):
            ge = etree.SubElement(guides_el, 'Guide')
            ge.set('id', gid)
            tours = etree.SubElement(ge, 'Tours')
            tours.set('count', str(g.total_tours))
            tours.set('total-participants', str(g.total_participants))
            etree.SubElement(ge, 'Revenue').text = str(g.revenue_generated)
            regs = etree.SubElement(ge, 'Regions')
            for r in sorted(g.regions):
                etree.SubElement(regs, 'Region').text = r
            langs = etree.SubElement(ge, 'Languages')
            for l in sorted(g.languages):
                etree.SubElement(langs, 'Language').text = l

        # Paths
        paths_el = etree.SubElement(root, 'PathStatistics')
        for pid, p in sorted(path_stats.items()):
            pe = etree.SubElement(paths_el, 'Path')
            pe.set('id', pid)
            usage = etree.SubElement(pe, 'Usage')
            usage.set('total-uses', str(p.total_trips))
            usage.set('total-participants', str(p.total_participants))
            usage.set('completion-rate', f"{p.completion_rate:.1f}")
            usage.set('avg-satisfaction', f"{p.avg_satisfaction:.2f}")

        # Also include legacy sections for older tests
        legacy_bikes = etree.SubElement(root, 'Bikes')
        for bid, b in sorted(bike_stats.items()):
            be = etree.SubElement(legacy_bikes, 'Bike')
            be.set('id', bid)
            etree.SubElement(be, 'TotalHours').text = str(int(b.total_hours))
            etree.SubElement(be, 'RentalHours').text = str(int(b.rental_hours))
            etree.SubElement(be, 'MaintenanceHours').text = str(int(b.maintenance_hours))
            etree.SubElement(be, 'Revenue').text = str(b.total_revenue)
            etree.SubElement(be, 'BookingCount').text = str(b.booking_count)
            etree.SubElement(be, 'OccupancyRate').text = f"{occupancy.get(bid, 0):.2f}"

        legacy_guides = etree.SubElement(root, 'Guides')
        for gid, g in sorted(guide_stats.items()):
            ge = etree.SubElement(legacy_guides, 'Guide')
            ge.set('id', gid)
            etree.SubElement(ge, 'TotalTours').text = str(g.total_tours)
            etree.SubElement(ge, 'TotalParticipants').text = str(g.total_participants)
            langs = etree.SubElement(ge, 'Languages')
            for l in sorted(g.languages):
                etree.SubElement(langs, 'Language').text = l
            regs = etree.SubElement(ge, 'Regions')
            for r in sorted(g.regions):
                etree.SubElement(regs, 'Region').text = r

        legacy_paths = etree.SubElement(root, 'Paths')
        for pid, p in sorted(path_stats.items()):
            pe = etree.SubElement(legacy_paths, 'Path')
            pe.set('id', pid)
            stats_el = etree.SubElement(pe, 'Statistics')
            stats_el.set('totalTrips', str(p.total_trips))
            stats_el.set('avgSatisfaction', f"{p.avg_satisfaction:.2f}")
            etree.SubElement(pe, 'RevenueGenerated').text = str(p.revenue_generated)

        return etree.tostring(root, pretty_print=True, encoding='unicode')
