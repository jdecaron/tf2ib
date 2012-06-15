CREATE TABLE files (
  fileName varchar(256) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL,
  `time` bigint(20) NOT NULL,
  PRIMARY KEY (fileName)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE statsIndex (
  id varchar(256) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL,
  files longtext CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (id)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
