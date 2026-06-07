CREATE TABLE IF NOT EXISTS topics (
  id SERIAL PRIMARY KEY,
  topic TEXT NOT NULL,
  used_at TIMESTAMPTZ,
  used_count INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS posts (
  id SERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  platform TEXT NOT NULL,
  topic TEXT,
  title TEXT,
  video_url TEXT,
  post_id TEXT,
  status TEXT DEFAULT 'pending',
  error_message TEXT
);

CREATE TABLE IF NOT EXISTS performance (
  id SERIAL PRIMARY KEY,
  post_id INT REFERENCES posts(id) ON DELETE CASCADE,
  checked_at TIMESTAMPTZ DEFAULT NOW(),
  views INT DEFAULT 0,
  likes INT DEFAULT 0,
  comments INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS leads (
  id SERIAL PRIMARY KEY,
  recorded_at TIMESTAMPTZ DEFAULT NOW(),
  source TEXT,
  whatsapp_member_count INT
);
