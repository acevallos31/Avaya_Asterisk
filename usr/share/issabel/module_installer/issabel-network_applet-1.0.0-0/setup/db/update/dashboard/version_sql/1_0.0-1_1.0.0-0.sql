BEGIN TRANSACTION;

INSERT INTO "applet" VALUES(50, 'Applet_IssabelNetwork', 'Issabel Network','system.png');

INSERT INTO "default_applet_by_user" VALUES(50, 50, 'admin');

INSERT INTO "activated_applet_by_user" VALUES(50, 50, 50, "admin");

COMMIT;


