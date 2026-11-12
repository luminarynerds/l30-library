# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from typing import List

logger = get_logger(__name__)

# Common Library of Congress Subject Headings
COMMON_LCSH = [
    # Fiction genres
    "Fiction",
    "Historical fiction",
    "Science fiction",
    "Fantasy fiction",
    "Mystery fiction",
    "Detective and mystery stories",
    "Suspense fiction",
    "Horror tales",
    "Love stories",
    "Romance fiction",
    "Adventure stories",
    "War stories",
    "Western stories",
    "Dystopian fiction",
    "Apocalyptic fiction",
    "Time travel fiction",
    "Space opera",
    "Cyberpunk fiction",
    "Steampunk fiction",
    # Non-fiction subjects
    "History",
    "Biography",
    "Autobiography",
    "Biographies",
    "Autobiographies",
    "Memoirs",
    "Self-help techniques",
    "Business",
    "Management",
    "Leadership",
    "Entrepreneurship",
    "Marketing",
    "Finance",
    "Economics",
    "Psychology",
    "Philosophy",
    "Religion",
    "Spirituality",
    "Science",
    "Technology",
    "Mathematics",
    "Physics",
    "Chemistry",
    "Biology",
    "Medicine",
    "Health",
    "Nutrition",
    "Exercise",
    "Cooking",
    "Food",
    "Travel",
    "Nature",
    "Environment",
    "Climate change",
    "Politics",
    "Government",
    "Law",
    "Education",
    "Social sciences",
    "Sociology",
    "Anthropology",
    "Geography",
    # Literature and arts
    "Poetry",
    "Drama",
    "Essays",
    "Literary criticism",
    "Art",
    "Music",
    "Theater",
    "Film",
    "Photography",
    "Architecture",
    "Design",
    # Children's and Young Adult
    "Children's stories",
    "Young adult fiction",
    "Picture books for children",
    "Juvenile fiction",
    "Juvenile literature",
    "Fairy tales",
    "Folklore",
    "Legends",
    "Mythology",
    # Specific topics
    "World War, 1939-1945",
    "World War, 1914-1918",
    "Civil War, 1861-1865",
    "American Revolution, 1775-1783",
    "Ancient history",
    "Medieval history",
    "Renaissance",
    "Industrial Revolution",
    "Women--History",
    "Women's rights",
    "Civil rights",
    "African Americans--History",
    "Slavery",
    "Immigration",
    "Social justice",
    "Human rights",
    "Wit and humor",
    "Satire",
    "Parody",
    # Technology and computing
    "Computer science",
    "Programming",
    "Artificial intelligence",
    "Machine learning",
    "Data science",
    "Internet",
    "Web development",
    "Cybersecurity",
    "Software engineering",
    # Family and relationships
    "Family",
    "Parenting",
    "Marriage",
    "Divorce",
    "Friendship",
    "Interpersonal relations",
    "Communication",
    # Sports and recreation
    "Sports",
    "Athletics",
    "Baseball",
    "Basketball",
    "Football",
    "Soccer",
    "Golf",
    "Tennis",
    "Running",
    "Hiking",
    "Camping",
    "Fishing",
    "Gardening",
    "Crafts",
    "Hobbies",
    # Language and linguistics
    "English language--Grammar",
    "English language--Composition and exercises",
    "Linguistics",
    "Foreign languages",
    "Spanish language",
    "French language",
    "German language",
    "Chinese language",
    # Special collections
    "Large print books",
    "Graphic novels",
    "Comics",
    "Manga",
    "Audiobooks",
    "Electronic books",
    "Reference books",
    "Encyclopedias",
    "Dictionaries",
]


class LCSHService:

    def __init__(self):
        # In production, this would load from a database table
        # For now, use the in-memory list
        self.subjects = sorted(COMMON_LCSH)
        self.subjects_lower = [s.lower() for s in self.subjects]

    def autocomplete(self, query: str, limit: int = 10) -> List[str]:
        if not query or not query.strip():
            return []

        query_lower = query.strip().lower()
        matches = []

        # First, find subjects that start with the query (prefix match)
        for idx, subject_lower in enumerate(self.subjects_lower):
            if subject_lower.startswith(query_lower):
                matches.append(self.subjects[idx])
                if len(matches) >= limit:
                    return matches

        # If we don't have enough matches, find subjects that contain the query
        if len(matches) < limit:
            for idx, subject_lower in enumerate(self.subjects_lower):
                if query_lower in subject_lower and self.subjects[idx] not in matches:
                    matches.append(self.subjects[idx])
                    if len(matches) >= limit:
                        return matches

        return matches

    def validate(self, subject: str) -> bool:
        if not subject:
            return False

        subject_lower = subject.strip().lower()
        return subject_lower in self.subjects_lower

    def get_similar(self, subject: str, limit: int = 5) -> List[str]:
        if not subject:
            return []

        # Split subject into words
        words = subject.lower().split()
        matches = []
        seen = set()

        # Find subjects that contain any of the words
        for word in words:
            for idx, subject_lower in enumerate(self.subjects_lower):
                if (
                    word in subject_lower
                    and self.subjects[idx] not in seen
                    and self.subjects[idx].lower() != subject.lower()
                ):
                    matches.append(self.subjects[idx])
                    seen.add(self.subjects[idx])
                    if len(matches) >= limit:
                        return matches

        return matches

    def get_all_starting_with(self, prefix: str, limit: int = 50) -> List[str]:
        if not prefix:
            return []

        prefix_lower = prefix.strip().lower()
        matches = []

        for idx, subject_lower in enumerate(self.subjects_lower):
            if subject_lower.startswith(prefix_lower):
                matches.append(self.subjects[idx])
                if len(matches) >= limit:
                    break

        return matches


# Singleton instance
lcsh_service = LCSHService()
