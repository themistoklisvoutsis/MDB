-- Skyline for: MIN budget, MAX popularity
SELECT m.*
FROM movies m
WHERE NOT EXISTS (
  SELECT 1
  FROM movies m2
  WHERE
    m2.budget <= m.budget
    AND m2.popularity >= m.popularity
    AND (m2.budget < m.budget OR m2.popularity > m.popularity)
)
ORDER BY m.budget ASC, m.popularity DESC;
