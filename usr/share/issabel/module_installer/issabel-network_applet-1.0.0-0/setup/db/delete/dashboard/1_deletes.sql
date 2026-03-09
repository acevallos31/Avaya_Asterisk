BEGIN TRANSACTION;

DELETE FROM "applet" WHERE id=50;

DELETE FROM "default_applet_by_user" WHERE id=50;

DELETE FROM "activated_applet_by_user" WHERE id=50;

COMMIT;


