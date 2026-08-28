INSERT INTO was_assignees (name)
VALUES
    ('Mina Salehi'),
    ('Tenesa Ellis'),
    ('Brycen Ford'),
    ('Zack Cogswell'),
    ('Justin Rothfleisch'),
    ('Oscar Saunders'),
    ('Wale Ojelabi')
ON CONFLICT (name) DO NOTHING;
