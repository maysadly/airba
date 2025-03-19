# Database Migrations

This directory contains the migration scripts for the database schema. Migrations are used to manage changes to the database structure over time, allowing you to apply and revert changes as needed.

## Getting Started

To create a new migration, use the following command:

```
flask db migrate -m "Description of the migration"
```

To apply the migration to the database, run:

```
flask db upgrade
```

To revert the last migration, use:

```
flask db downgrade
```

## Best Practices

- Always provide a meaningful message when creating a migration.
- Review the generated migration script before applying it to ensure it accurately reflects the intended changes.
- Regularly back up your database, especially before applying migrations.