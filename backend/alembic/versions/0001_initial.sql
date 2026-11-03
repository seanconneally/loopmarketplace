-- Initial schema snapshot. Do not regenerate after release.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE blocks (
	blocker_id UUID NOT NULL, 
	blocked_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_blocks PRIMARY KEY (id), 
	CONSTRAINT uq_blocks_blocker_id UNIQUE (blocker_id, blocked_id)
);

CREATE INDEX ix_blocks_reverse ON blocks (blocked_id, blocker_id);

CREATE TABLE conversations (
	listing_id UUID NOT NULL, 
	buyer_id UUID NOT NULL, 
	seller_id UUID NOT NULL, 
	last_message_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_conversations PRIMARY KEY (id), 
	CONSTRAINT uq_conversations_listing_id UNIQUE (listing_id, buyer_id)
);

CREATE INDEX ix_conversation_buyer ON conversations (buyer_id, created_at);

CREATE INDEX ix_conversation_seller ON conversations (seller_id, created_at);

CREATE TABLE dead_letters (
	outbox_id UUID NOT NULL, 
	event_type VARCHAR(80) NOT NULL, 
	error_code VARCHAR(100) NOT NULL, 
	replayed_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_dead_letters PRIMARY KEY (id), 
	CONSTRAINT uq_dead_letters_outbox_id UNIQUE (outbox_id)
);

CREATE TABLE dealer_imports (
	user_id UUID NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	csv_text VARCHAR(200000) NOT NULL, 
	rows JSONB NOT NULL, 
	idempotency_key VARCHAR(180) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_dealer_imports PRIMARY KEY (id), 
	CONSTRAINT uq_dealer_imports_idempotency_key UNIQUE (idempotency_key)
);

CREATE TABLE events (
	user_id UUID NOT NULL, 
	listing_id UUID NOT NULL, 
	event_type VARCHAR(20) NOT NULL, 
	value FLOAT NOT NULL, 
	client_event_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_events PRIMARY KEY (id), 
	CONSTRAINT uq_events_user_id UNIQUE (user_id, client_event_id), 
	CONSTRAINT ck_events_event_value CHECK (value >= 0 and value <= 3600)
);

CREATE INDEX ix_events_listing ON events (listing_id, event_type, created_at);

CREATE INDEX ix_events_time ON events USING brin (created_at);

CREATE TABLE feed_candidates (
	listing_id UUID NOT NULL, 
	seller_id UUID NOT NULL, 
	region_id VARCHAR(30) NOT NULL, 
	location geography(POINT,4326) NOT NULL, 
	price_cents INTEGER NOT NULL, 
	make VARCHAR(50) NOT NULL, 
	year INTEGER NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	engagement FLOAT NOT NULL, 
	public_data JSONB NOT NULL, 
	CONSTRAINT pk_feed_candidates PRIMARY KEY (listing_id)
);

CREATE INDEX ix_feed_filters ON feed_candidates (region_id, make, year, price_cents);

CREATE INDEX ix_feed_location ON feed_candidates USING gist (location);

CREATE INDEX ix_feed_recency ON feed_candidates (region_id, published_at, listing_id);

CREATE TABLE listings (
	seller_id UUID NOT NULL, 
	category VARCHAR(30) NOT NULL, 
	region_id VARCHAR(30) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	title VARCHAR(120) NOT NULL, 
	description VARCHAR(3000) NOT NULL, 
	price_cents INTEGER NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	latitude FLOAT NOT NULL, 
	longitude FLOAT NOT NULL, 
	area VARCHAR(100) NOT NULL, 
	rights_confirmed BOOLEAN NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	sold_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_listings PRIMARY KEY (id), 
	CONSTRAINT uq_listings_seller_id UNIQUE (seller_id, idempotency_key), 
	CONSTRAINT ck_listings_positive_price CHECK (price_cents > 0), 
	CONSTRAINT ck_listings_coordinates CHECK (latitude between -90 and 90 and longitude between -180 and 180), 
	CONSTRAINT ck_listings_valid_status CHECK (status in ('draft','processing','pending_review','live','sold','removed','failed'))
);

CREATE INDEX ix_listings_live_recency ON listings (published_at, id) WHERE status = 'live';

CREATE INDEX ix_listings_seller_id ON listings (seller_id);

CREATE TABLE media_assets (
	listing_id UUID NOT NULL, 
	provider VARCHAR(30) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	object_key VARCHAR(240) NOT NULL, 
	upload_id VARCHAR(300) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	content_type VARCHAR(50) NOT NULL, 
	playback_url VARCHAR(500), 
	poster_url VARCHAR(500), 
	duration FLOAT, 
	perceptual_hash VARCHAR(32), 
	idempotency_key VARCHAR(128) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_media_assets PRIMARY KEY (id), 
	CONSTRAINT ck_media_assets_size_limit CHECK (size_bytes > 0 and size_bytes <= 524288000), 
	CONSTRAINT uq_media_assets_listing_id UNIQUE (listing_id), 
	CONSTRAINT uq_media_assets_object_key UNIQUE (object_key)
);

CREATE INDEX ix_media_assets_perceptual_hash ON media_assets (perceptual_hash);

CREATE TABLE moderation_actions (
	moderator_id UUID NOT NULL, 
	target_type VARCHAR(20) NOT NULL, 
	target_id UUID NOT NULL, 
	action VARCHAR(20) NOT NULL, 
	reason VARCHAR(1000) NOT NULL, 
	appeal_status VARCHAR(20), 
	notified_at TIMESTAMP WITH TIME ZONE, 
	idempotency_key VARCHAR(128) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_moderation_actions PRIMARY KEY (id), 
	CONSTRAINT uq_moderation_actions_idempotency_key UNIQUE (idempotency_key)
);

CREATE TABLE notifications (
	user_id UUID NOT NULL, 
	event_id UUID NOT NULL, 
	kind VARCHAR(30) NOT NULL, 
	payload JSONB NOT NULL, 
	channel VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_notifications PRIMARY KEY (id), 
	CONSTRAINT uq_notifications_event_id UNIQUE (event_id)
);

CREATE INDEX ix_notifications_user_id ON notifications (user_id);

CREATE TABLE outbox (
	event_type VARCHAR(80) NOT NULL, 
	payload JSONB NOT NULL, 
	available_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	lease_until TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	attempts INTEGER NOT NULL, 
	last_error TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_outbox PRIMARY KEY (id)
);

CREATE INDEX ix_outbox_pending ON outbox (available_at) WHERE completed_at IS NULL;

CREATE TABLE refresh_sessions (
	user_id UUID NOT NULL, 
	family_id UUID NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	used_at TIMESTAMP WITH TIME ZONE, 
	revoked BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_refresh_sessions PRIMARY KEY (id), 
	CONSTRAINT uq_refresh_sessions_token_hash UNIQUE (token_hash)
);

CREATE INDEX ix_refresh_sessions_family ON refresh_sessions (family_id);

CREATE INDEX ix_refresh_sessions_user ON refresh_sessions (user_id);

CREATE TABLE reports (
	reporter_id UUID, 
	target_type VARCHAR(20) NOT NULL, 
	target_id UUID NOT NULL, 
	reason VARCHAR(1000) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_reports PRIMARY KEY (id), 
	CONSTRAINT uq_reports_idempotency_key UNIQUE (idempotency_key)
);

CREATE INDEX ix_reports_queue ON reports (status, created_at, id);

CREATE TABLE users (
	phone VARCHAR(20) NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	email VARCHAR(254), 
	role VARCHAR(12) NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	verified_at TIMESTAMP WITH TIME ZONE, 
	adult_declared BOOLEAN NOT NULL, 
	analytics_consent BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_users PRIMARY KEY (id), 
	CONSTRAINT ck_users_valid_role CHECK (role in ('member','dealer','admin')), 
	CONSTRAINT ck_users_valid_status CHECK (status in ('active','suspended','deleted')), 
	CONSTRAINT uq_users_phone UNIQUE (phone), 
	CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE TABLE viewings (
	conversation_id UUID NOT NULL, 
	proposed_by UUID NOT NULL, 
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	place VARCHAR(300) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	revision INTEGER NOT NULL, 
	history JSONB NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	reminded_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_viewings PRIMARY KEY (id), 
	CONSTRAINT uq_viewings_conversation_id UNIQUE (conversation_id, idempotency_key), 
	CONSTRAINT ck_viewings_valid_status CHECK (status in ('proposed','accepted','declined','cancelled'))
);

CREATE INDEX ix_viewings_conversation ON viewings (conversation_id, id);

CREATE INDEX ix_viewings_reminder ON viewings (status, starts_at) WHERE reminded_at IS NULL;

CREATE TABLE car_details (
	listing_id UUID NOT NULL, 
	make VARCHAR(50) NOT NULL, 
	model VARCHAR(60) NOT NULL, 
	year INTEGER NOT NULL, 
	mileage_km INTEGER NOT NULL, 
	fuel VARCHAR(20) NOT NULL, 
	transmission VARCHAR(20) NOT NULL, 
	CONSTRAINT pk_car_details PRIMARY KEY (listing_id), 
	CONSTRAINT ck_car_details_year_range CHECK (year between 1900 and 2100), 
	CONSTRAINT ck_car_details_nonnegative_mileage CHECK (mileage_km >= 0), 
	CONSTRAINT fk_car_details_listing_id_listings FOREIGN KEY(listing_id) REFERENCES listings (id) ON DELETE CASCADE
);

CREATE TABLE dealers (
	user_id UUID NOT NULL, 
	business_name VARCHAR(120) NOT NULL, 
	registration_number VARCHAR(80) NOT NULL, 
	address VARCHAR(240) NOT NULL, 
	verified_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_dealers PRIMARY KEY (id), 
	CONSTRAINT uq_dealers_user_id UNIQUE (user_id), 
	CONSTRAINT fk_dealers_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE messages (
	conversation_id UUID NOT NULL, 
	sender_id UUID NOT NULL, 
	body VARCHAR(4000) NOT NULL, 
	message_type VARCHAR(20) NOT NULL, 
	viewing_id UUID, 
	idempotency_key VARCHAR(128) NOT NULL, 
	warnings JSONB NOT NULL, 
	read_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_messages PRIMARY KEY (id), 
	CONSTRAINT uq_messages_conversation_id UNIQUE (conversation_id, sender_id, idempotency_key), 
	CONSTRAINT fk_messages_conversation_id_conversations FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);

CREATE INDEX ix_messages_history ON messages (conversation_id, created_at, id);

CREATE TABLE saves (
	user_id UUID NOT NULL, 
	listing_id UUID NOT NULL, 
	CONSTRAINT pk_saves PRIMARY KEY (user_id, listing_id), 
	CONSTRAINT fk_saves_listing_id_listings FOREIGN KEY(listing_id) REFERENCES listings (id) ON DELETE CASCADE
);

CREATE INDEX ix_saves_listing ON saves (listing_id);
