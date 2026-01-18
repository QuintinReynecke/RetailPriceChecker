import re

text_1 = "3.8 3.8 out of 5 stars    156 ratings | Search this page"
text_2 = "4.9 4.9 out of 5 stars    26 ratings | Search this page"
text_3 = "100 global ratings"
text_4 = "5 stars"
text_5 = "1,234 customer reviews"

pattern = r'(\d+[\d,]*)\s+(?:global\s+|customer\s+)?(?:ratings|reviews)'

print(f"Pattern: {pattern}")
for t in [text_1, text_2, text_3, text_4, text_5]:
    match = re.search(pattern, t, re.IGNORECASE)
    print(f"'{t}' -> {match.group(1) if match else 'No match'}")
