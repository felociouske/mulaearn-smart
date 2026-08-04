from django.core.management.base import BaseCommand

from surveys.models import SurveyQuestion

# 40 general-knowledge questions to start with — safe, uncontroversial
# facts (geography, science, math, history). Add the remaining ~60
# through the Django admin; get_or_create below makes re-running this
# command safe if you also add more questions here later.
QUESTIONS = [
    ("What is the capital of Kenya?", ["Mombasa", "Nairobi", "Kisumu", "Nakuru"], 1),
    ("What is the capital of France?", ["Paris", "Lyon", "Marseille", "Nice"], 0),
    ("How many continents are there?", ["5", "6", "7", "8"], 2),
    ("What is the largest ocean on Earth?", ["Atlantic", "Indian", "Arctic", "Pacific"], 3),
    ("What is the chemical symbol for water?", ["H2O", "CO2", "O2", "NaCl"], 0),
    ("How many days are there in a leap year?", ["364", "365", "366", "367"], 2),
    ("What is the largest planet in our solar system?", ["Earth", "Jupiter", "Saturn", "Mars"], 1),
    ("What is the smallest prime number?", ["0", "1", "2", "3"], 2),
    ("Which gas do plants absorb from the atmosphere?", ["Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen"], 2),
    ("What is the freezing point of water in Celsius?", ["0°C", "32°C", "100°C", "-10°C"], 0),
    ("What is the longest river in the world?", ["Amazon", "Nile", "Yangtze", "Mississippi"], 1),
    ("How many sides does a hexagon have?", ["5", "6", "7", "8"], 1),
    ("What is the currency of Kenya?", ["Shilling", "Naira", "Rand", "Cedi"], 0),
    ("What is the tallest mountain in Africa?", ["Mount Kenya", "Kilimanjaro", "Table Mountain", "Atlas Mountains"], 1),
    ("How many legs does a spider have?", ["6", "8", "10", "12"], 1),
    ("What is the powerhouse of the cell called?", ["Nucleus", "Ribosome", "Mitochondria", "Cytoplasm"], 2),
    ("What is 12 multiplied by 12?", ["124", "144", "134", "154"], 1),
    ("What is the square root of 81?", ["7", "8", "9", "10"], 2),
    ("Which planet is known as the Red Planet?", ["Venus", "Mars", "Jupiter", "Mercury"], 1),
    ("What is the main language spoken in Brazil?", ["Spanish", "Portuguese", "French", "Italian"], 1),
    ("How many strings does a standard guitar have?", ["4", "5", "6", "7"], 2),
    ("What is the boiling point of water in Celsius?", ["90°C", "100°C", "110°C", "120°C"], 1),
    ("What is the largest mammal in the world?", ["Elephant", "Blue whale", "Giraffe", "Hippopotamus"], 1),
    ("How many colors are in a rainbow?", ["5", "6", "7", "8"], 2),
    ("What is the capital of Japan?", ["Osaka", "Kyoto", "Tokyo", "Yokohama"], 2),
    ("What organ pumps blood through the body?", ["Lungs", "Liver", "Heart", "Kidney"], 2),
    ("What is the fastest land animal?", ["Lion", "Cheetah", "Horse", "Antelope"], 1),
    ("How many bones are in the adult human body?", ["186", "206", "226", "246"], 1),
    ("What is the capital of Egypt?", ["Alexandria", "Giza", "Cairo", "Luxor"], 2),
    ("Which planet has the most moons?", ["Earth", "Mars", "Saturn", "Mercury"], 2),
    ("What is 15% of 200?", ["20", "25", "30", "35"], 2),
    ("What is the largest desert in the world?", ["Sahara", "Gobi", "Antarctic", "Kalahari"], 2),
    ("Which country gifted the Statue of Liberty to the USA?", ["UK", "France", "Spain", "Italy"], 1),
    ("What is the study of living organisms called?", ["Physics", "Chemistry", "Biology", "Geology"], 2),
    ("How many players are on a football (soccer) team on the field?", ["9", "10", "11", "12"], 2),
    ("What is the closest star to Earth?", ["Alpha Centauri", "Polaris", "The Sun", "Sirius"], 2),
    ("What gas do humans need to breathe to survive?", ["Carbon dioxide", "Oxygen", "Nitrogen", "Helium"], 1),
    ("What shape has three sides?", ["Square", "Triangle", "Pentagon", "Hexagon"], 1),
    ("What is the largest country in Africa by land area?", ["Nigeria", "Algeria", "Egypt", "South Africa"], 1),
    ("How many minutes are in a full day?", ["1240", "1400", "1440", "1500"], 2),
]


class Command(BaseCommand):
    help = "Seeds starter survey questions. Safe to re-run — skips questions that already exist."

    def handle(self, *args, **options):
        created_count = 0
        for text, options_list, correct_index in QUESTIONS:
            _, created = SurveyQuestion.objects.get_or_create(
                text=text,
                defaults={"options": options_list, "correct_option": correct_index},
            )
            if created:
                created_count += 1

        total = SurveyQuestion.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Created {created_count} new question(s). Pool now has {total} question(s) total "
            f"(add more via /admin/surveys/surveyquestion/ to reach 100)."
        ))