// src/auth/schemas.ts
// Example - adjust based on your actual User model and FastAPI Users schemas
import { UUID } from 'crypto'; // Or appropriate UUID type

export interface UserRead {
    id: UUID;
    email: string;
    is_active: boolean;
    is_superuser: boolean;
    is_verified: boolean; // Add if you use verification
    // Add any other fields you expose in UserRead schema
}

export interface UserCreate {
    email: string;
    password: string;
    // Add any other required fields for creation
}

export interface UserUpdate {
    email?: string;
    password?: string;
    is_active?: boolean;
    is_superuser?: boolean;
    is_verified?: boolean;
     // Add any other updatable fields
}