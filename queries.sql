-- Open output/demo/books.sqlite or output/live/books.sqlite in an SQLite client.
SELECT title, price_gbp FROM books ORDER BY price_gbp LIMIT 5;

SELECT rating, COUNT(*) AS book_count, ROUND(AVG(price_gbp), 2) AS average_price_gbp
FROM books
GROUP BY rating
ORDER BY rating;

SELECT title, price_gbp FROM books WHERE in_stock = 1 AND price_gbp < 20;
