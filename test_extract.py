from bs4 import BeautifulSoup
import re

with open("test_out.html") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# In blinkit, product title usually in something like Product__Content or just <div> with some class.
# Let's just find things that look like price (₹...)
all_text = soup.get_text(separator='|', strip=True)

# print a snippet of text around a price
prices = re.finditer(r'₹[0-9]+', all_text)
for i, match in enumerate(prices):
    if i > 5: break
    start = max(0, match.start() - 50)
    end = min(len(all_text), match.end() + 50)
    print("Match:", all_text[start:end])
