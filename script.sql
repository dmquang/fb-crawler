-- Tạo bảng admin.users
CREATE TABLE admin.users (
    username VARCHAR(45) PRIMARY KEY,
    password VARCHAR(45),
    link_scan_limit INT,
    link_follow_limit INT,  
    link_hide_limit INT,    
    expire_time INT,
    permission VARCHAR(45)
);

-- Tạo bảng admin.cookies
CREATE TABLE admin.cookies (
    cookie_id INT PRIMARY KEY,
    cookie VARCHAR(1000),
    status VARCHAR(45)
);

-- Tạo bảng user.comments
CREATE TABLE user.comments (
    comment_id VARCHAR(100) PRIMARY KEY,
    post_id VARCHAR(100),
    post_name TEXT,
    author_id VARCHAR(100),   
    author_name VARCHAR(100),
    author_avatar VARCHAR(1000),
    content TEXT,
    info VARCHAR(1000),
    phone_number VARCHAR(100),
    created_time INT,
    username VARCHAR(45)
);

-- Tạo bảng user.cookies
CREATE TABLE user.cookies (
    cookie_id VARCHAR(100) PRIMARY KEY,
    cookie TEXT,
    status VARCHAR(45),
    username VARCHAR(45)
);

-- Tạo bảng user.proxies
CREATE TABLE user.proxies (
    proxy VARCHAR(500) PRIMARY KEY,
    status VARCHAR(45),
    username VARCHAR(45)
);

-- Tạo bảng user.posts
CREATE TABLE user.posts (
    post_id VARCHAR(100),
    post_name VARCHAR(100) PRIMARY KEY,
    post_url varchar(400),
    reaction_count INT,
    comment_count INT,
    time_created INT,
    last_comment INT,
    delay INT,
    status varchar(45),
    username VARCHAR(45)
);


CREATE TABLE user.stopped_posts (
    post_id VARCHAR(100),
    post_name VARCHAR(100) PRIMARY KEY,
    post_url varchar(400),
    reaction_count INT,
    comment_count INT,
    time_created INT,
    last_comment INT,
    delay INT,
    status varchar(45),
    username VARCHAR(45),
    stopped_time TEXT
);

CREATE TABLE user.stopped_posts (
    post_id VARCHAR(100),
    post_name VARCHAR(100) PRIMARY KEY,
    post_url varchar(400),
    reaction_count INT,
    comment_count INT,
    time_created INT,
    last_comment INT,
    delay INT,
    status varchar(45),
    username VARCHAR(45),
    stopped_time INT
);