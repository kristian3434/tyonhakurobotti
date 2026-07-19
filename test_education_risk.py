import unittest

from config import USER_EDUCATION
from scoring import calculate_match_analysis, classify_education_risk


class EducationRiskTests(unittest.TestCase):
    def test_requested_examples(self):
        cases = [
            ("Toivomme sinulta soveltuvaa korkeakoulututkintoa.", "medium"),
            ("Edellytämme soveltuvaa korkeakoulututkintoa.", "high"),
            ("Kelpoisuusvaatimuksena on soveltuva korkeakoulututkinto.", "blocking"),
            ("Alan koulutus katsotaan eduksi, mutta tärkeintä on portfolio.", "low"),
            (
                "Sinulla on tradenomin, medianomin tai muun soveltuvan "
                "korkeakoulututkinnon tausta.",
                "high",
            ),
            ("Kokemus digimarkkinoinnista ja vahva portfolio ovat tärkeimpiä.", "low"),
            ("Vaaditaan soveltuva korkeakoulututkinto.", "blocking"),
            ("AMK-tutkinto katsotaan eduksi.", "medium"),
            ("Edellytämme tehtävään soveltuvaa koulutusta.", "high"),
            ("Vaaditaan alan tutkinto tai vastaava koulutus.", "high"),
            ("Tehtävään ei vaadita tutkintoa, vaan portfolio ratkaisee.", "low"),
            ("Vaaditaan motivaatiota ja hyvää asennetta. Koulutamme sinut tehtävään.", "low"),
        ]

        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(classify_education_risk(text), expected)

    def test_public_demo_has_no_saved_education_profile(self):
        self.assertEqual(USER_EDUCATION["degree"], "")
        self.assertEqual(USER_EDUCATION["level"], "")
        self.assertIsNone(USER_EDUCATION["year"])
        self.assertFalse(USER_EDUCATION["is_higher_education"])
        self.assertFalse(USER_EDUCATION["has_amk_degree"])
        self.assertFalse(USER_EDUCATION["has_university_degree"])

    def test_high_and_blocking_cap_overall_score(self):
        high = calculate_match_analysis(
            "Edellytämme soveltuvaa korkeakoulututkintoa.",
            skill_match_score=95,
        )
        blocking = calculate_match_analysis(
            "Vaaditaan soveltuva korkeakoulututkinto.",
            skill_match_score=95,
        )

        self.assertEqual(high["recommendation_level"], "high_risk")
        self.assertLessEqual(high["overall_match_score"], 65)
        self.assertEqual(blocking["recommendation_level"], "do_not_recommend")
        self.assertLessEqual(blocking["overall_match_score"], 45)


if __name__ == "__main__":
    unittest.main()
