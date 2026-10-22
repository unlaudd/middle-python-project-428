"""Migration to add NOT NULL constraints and CHECK constraints.

Adds NOT NULL to foreign keys and CHECK constraint for booking status.
"""

from yoyo import step

__depends__ = {"0001_initial_schema"}

steps = [
    step(
        """
        -- Add NOT NULL to foreign keys
        ALTER TABLE flights ALTER COLUMN airline_code SET NOT NULL;
        ALTER TABLE flights ALTER COLUMN origin_code SET NOT NULL;
        ALTER TABLE flights ALTER COLUMN destination_code SET NOT NULL;
        ALTER TABLE bookings ALTER COLUMN flight_id SET NOT NULL;
        ALTER TABLE passengers ALTER COLUMN booking_code SET NOT NULL;

        -- Add CHECK constraint for booking status
        ALTER TABLE bookings ADD CONSTRAINT chk_booking_status 
            CHECK (status IN ('confirmed', 'cancelled'));
        """,
        """
        -- Rollback constraints
        ALTER TABLE bookings DROP CONSTRAINT IF EXISTS chk_booking_status;
        
        ALTER TABLE passengers ALTER COLUMN booking_code DROP NOT NULL;
        ALTER TABLE bookings ALTER COLUMN flight_id DROP NOT NULL;
        ALTER TABLE flights ALTER COLUMN destination_code DROP NOT NULL;
        ALTER TABLE flights ALTER COLUMN origin_code DROP NOT NULL;
        ALTER TABLE flights ALTER COLUMN airline_code DROP NOT NULL;
        """,
    )
]
