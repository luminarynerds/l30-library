-- Add CLAWED_BACK to royalty transaction status enum
ALTER TYPE royaltytransactionstatus ADD VALUE IF NOT EXISTS 'clawed_back';
