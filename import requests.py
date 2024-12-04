import requests
from bs4 import BeautifulSoup

def get_product_prices(url):
    """Scrapes product prices from a given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        soup = BeautifulSoup(response.content, "html.parser")
        # **CRITICAL:**  Replace the next line with the correct CSS selector for the product prices on the *specific* website you're targeting.  Inspect the website's HTML to find this selector.
        price_elements = soup.select(".price-element-class")  # Example:  Find elements with the class "price-element-class"

        prices = [float(price.text.replace("$", "").strip()) for price in price_elements]
        return prices
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None
    except Exception as e:
        print(f"Error scraping prices: {e}")
        return None

# Example usage:
url = "https://www.example-ecommerce-website.com/products"  # **REPLACE with the actual URL**
prices = get_product_prices(url)
if prices:
    print(prices)
    