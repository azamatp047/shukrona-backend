from sqlalchemy import text
from app.database import engine

def migrate():
    with engine.connect() as conn:
        print("Starting manual migration...")
        
        # Add user_type to users
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN user_type VARCHAR DEFAULT 'standard';"))
            print("Added user_type to users table")
        except Exception as e:
            print(f"users.user_type error: {e}")
            
        # Add columns to orders
        try:
            conn.execute(text("ALTER TABLE orders ADD COLUMN base_total_amount FLOAT DEFAULT 0.0;"))
            conn.execute(text("ALTER TABLE orders ADD COLUMN final_total_amount FLOAT DEFAULT 0.0;"))
            conn.execute(text("ALTER TABLE orders ADD COLUMN is_price_locked BOOLEAN DEFAULT FALSE;"))
            print("Added columns to orders table")
        except Exception as e:
            print(f"orders columns error: {e}")

        # Create order_price_history table if it doesn't exist
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS order_price_history (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER REFERENCES orders(id),
                    courier_id INTEGER REFERENCES couriers(id),
                    previous_price FLOAT,
                    new_price FLOAT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            print("Created order_price_history table")
        except Exception as e:
            print(f"order_price_history error: {e}")
        
        conn.commit()
        print("Migration completed!")

if __name__ == "__main__":
    migrate()
