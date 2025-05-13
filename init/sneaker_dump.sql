-- =============== CLIENTS TABLE ===============
CREATE TABLE IF NOT EXISTS client (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(150) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'client'
);

-- =============== SNEAKERS TABLE ===============
CREATE TABLE IF NOT EXISTS sneakers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description VARCHAR(500) NOT NULL,
    price FLOAT NOT NULL,
    image_url VARCHAR(300) NOT NULL,
    brand VARCHAR(50) DEFAULT 'Unknown',
    is_featured BOOLEAN DEFAULT FALSE
);



-- =============== CART ITEM TABLE ===============

CREATE TABLE IF NOT EXISTS cart_item (
    id SERIAL PRIMARY KEY,
    sneaker_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    size VARCHAR(10) NOT NULL, 
    FOREIGN KEY (sneaker_id) REFERENCES sneakers(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES client(id) ON DELETE CASCADE
);

