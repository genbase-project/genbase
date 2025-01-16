What is a Schema?
A schema is a namespace that contains named database objects such as tables, views, indexes, data types, functions, operators and other objects. Schemas provide:

Organization of database objects into logical groups
Multiple users can use one database without interfering with each other
Third-party applications can be put into separate schemas to avoid name collisions

Default Schema

public is the default schema in PostgreSQL
When no schema is specified, objects are created in the public schema
The search path determines which schemas are searched (SHOW search_path;)

Schema Management
Creating Schemas
sqlCopyCREATE SCHEMA schema_name;
CREATE SCHEMA IF NOT EXISTS schema_name;
CREATE SCHEMA schema_name AUTHORIZATION user_name;
Using Schemas
sqlCopy-- Fully qualified names
schema_name.table_name

-- Setting search path
SET search_path TO schema_name, public;
Dropping Schemas
sqlCopyDROP SCHEMA schema_name;
DROP SCHEMA IF EXISTS schema_name CASCADE;  -- Removes dependent objects
Best Practices
Schema Organization

Application-Based Separation

Different applications use different schemas
Prevents naming conflicts
Easier access control


Functional Separation

core - Core business logic
audit - Audit tables
reporting - Reporting views
staging - Data loading/ETL


Team-Based Separation

Different teams work in different schemas
Reduces coordination overhead
Clear ownership



Naming Conventions

Use lowercase names
Use underscores for spaces
Be consistent with pluralization
Prefix temporary schemas
Use descriptive but concise names

Security Considerations

Schema Level Permissions
sqlCopyGRANT USAGE ON SCHEMA schema_name TO role_name;
GRANT CREATE ON SCHEMA schema_name TO role_name;

Default Privileges
sqlCopyALTER DEFAULT PRIVILEGES IN SCHEMA schema_name 
GRANT SELECT ON TABLES TO read_only_role;

Schema Ownership

Consider using group roles for schema ownership
Separate schema ownership from object ownership



Performance Considerations

Search Path

Keep search path short
Be explicit in production code
Consider performance impact of schema searches


Schema Size

Monitor schema growth
Consider partitioning large schemas
Regular maintenance of large schemas


Cross-Schema Queries

Use fully qualified names in production
Index foreign key relationships
Consider materialized views for complex cross-schema queries



Common Patterns
Multi-tenant Schemas

One schema per tenant
Shared schema with tenant ID column
Hybrid approaches

Versioning Schemas

Schema versioning for major changes
Version in schema name
Migration strategies between versions

Temporary Schemas

Use for ETL processes
Cleanup procedures
Naming conventions for temp schemas

Monitoring and Maintenance
Size Monitoring
sqlCopySELECT schemaname, pg_size_pretty(sum(pg_total_relation_size(schemaname || '.' || tablename))::bigint)
FROM pg_tables
GROUP BY schemaname;
Object Counts
sqlCopySELECT schemaname, count(*)
FROM pg_tables
GROUP BY schemaname;
Permissions Audit
sqlCopySELECT grantor, grantee, privilege_type, table_schema
FROM information_schema.role_table_grants
WHERE table_schema = 'schema_name';
Common Issues and Solutions
Name Collisions

Use schema qualifiers
Consistent naming conventions
Regular audits of object names

Permission Issues

Check search path
Verify schema ownership
Review default privileges

Performance Problems

Monitor schema size
Review cross-schema queries
Check index usage

Migration Strategies
Schema Changes

Create new schema version
Migrate data
Switch applications
Remove old schema

Zero-Downtime Migrations

Create new schema
Copy structure
Sync data
Switch over
Cleanup

Tools and Extensions

pg_dump for schema backups
information_schema for metadata
Schema diff tools
Migration frameworks