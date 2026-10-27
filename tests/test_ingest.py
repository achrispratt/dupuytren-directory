"""Unit tests for the ingestion helpers. Run: python3 -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "ingest"))

from lib import clean_person, country_code, person_key, region_code  # noqa: E402
from merge import candidates, merge  # noqa: E402
from sources import _bds_people, _notes_to_tx  # noqa: E402


def entry(name, city, region, cc, tx, source="ids_na_na", website=None):
    return {
        "people": [{"name": name, "honorific": "Dr"}], "practice": None, "street": None, "city": city,
        "region": region, "postal": None, "country": cc, "phone": None, "website": website, "email": None,
        "note": None, "treatments": tx, "flags": [], "specialty": "hand_surgery",
        "source": {"id": source, "url": "u", "page_modified": None, "label": "l", "kind": "patient_org_list"},
        "extra_locations": [], "location_precision": "city",
    }


class Names(unittest.TestCase):
    def test_titles_and_credentials(self):
        self.assertEqual(clean_person("Dr. Prosper Benhaim (CHS)"), ("Prosper Benhaim", "Dr"))
        self.assertEqual(clean_person("William B Ericson Jr MD FACS FAAOS")[0], "William B Ericson Jr")
        self.assertEqual(clean_person("Stuart D. Patterson, MD, FRCSC")[0], "Stuart D. Patterson")
        self.assertEqual(clean_person("Prof. Dr. Leung-kim HUNG")[0], "Leung-kim HUNG")
        self.assertEqual(clean_person("PD Dr Fabian Fehlauer"), ("Fabian Fehlauer", "PD Dr"))

    def test_last_first(self):
        self.assertEqual(clean_person("Smith, Maggi")[0], "Maggi Smith")
        self.assertEqual(clean_person("Jorge F. Clifton, Dr.")[0], "Jorge F. Clifton")

    def test_person_key_ignores_middle_and_accents(self):
        self.assertEqual(person_key("Gary M. Pess"), person_key("Gary Pess"))
        self.assertEqual(person_key("Philip Sauvé"), person_key("Philip Sauve"))

    def test_bds_groups(self):
        people, group = _bds_people("Drs Ribak, Borkowski, Avila, de Andrade")
        self.assertTrue(group)
        self.assertEqual(len(people), 4)
        people, group = _bds_people("Dr Gary Pess")
        self.assertFalse(group)
        self.assertEqual(people[0]["name"], "Gary Pess")


class Codes(unittest.TestCase):
    def test_country_and_region(self):
        self.assertEqual(country_code("UK"), "GB")
        self.assertEqual(country_code("Soutn Africa"), "ZA")
        self.assertEqual(region_code("New Jersey", "US"), "NJ")
        self.assertEqual(region_code("british columbia", "CA"), "BC")

    def test_notes(self):
        tx, flags = _notes_to_tx("- fasciectomy | - needle aponevrotomy (NA) | - collagenase injection (Xiaflex)")
        self.assertEqual({t[0] for t in tx}, {"fasciectomy", "needle_aponeurotomy", "collagenase"})
        tx, _ = _notes_to_tx("surgery, conservative treatment", foot_layer=True)
        self.assertIn(["foot_surgery", "foot"], tx)
        self.assertNotIn(["fasciectomy", "hand"], tx)
        _, flags = _notes_to_tx("RT friendly")
        self.assertIn("rt_referral", flags)


class Merging(unittest.TestCase):
    def test_same_doctor_two_lists_merges(self):
        a = entry("Gary Pess", "Eatontown", "NJ", "US", [["needle_aponeurotomy", "hand"]])
        b = entry("Gary M. Pess", "Eatontown", "NJ", "US", [["collagenase", "hand"]], source="bds_map")
        m = merge(candidates([a, b]))
        self.assertEqual(len(m), 1)
        self.assertEqual(set(m[0]["treatments"]), {"needle_aponeurotomy:hand", "collagenase:hand"})
        self.assertEqual(len(m[0]["sources"]), 2)

    def test_namesakes_in_different_states_stay_apart(self):
        a = entry("John Smith", "Boston", "MA", "US", [["fasciectomy", "hand"]])
        b = entry("John Smith", "Dallas", "TX", "US", [["fasciectomy", "hand"]], source="bds_map")
        self.assertEqual(len(merge(candidates([a, b]))), 2)

    def test_surname_only_does_not_merge_with_full_name(self):
        a = entry("Kelly", "Sheffield", None, "GB", [["fasciectomy", "hand"]])
        b = entry("Michael Kelly", "Sheffield", None, "GB", [["fasciectomy", "hand"]])
        self.assertEqual(len(merge(candidates([a, b]))), 2)


if __name__ == "__main__":
    unittest.main()
