-- 2026-04-09 更新：为 test_case 表增加断言（校验）相关字段
-- assert_keyword: 响应文本包含的关键字
ALTER TABLE test_case ADD COLUMN assert_keyword VARCHAR(255) NULL;

-- assert_json_field: JSON 路径校验，例如 {"$.code": 200}
ALTER TABLE test_case ADD COLUMN assert_json_field TEXT NULL;

-- assert_max_time: 最大响应耗时校验
ALTER TABLE test_case ADD COLUMN assert_max_time VARCHAR(20) NULL;