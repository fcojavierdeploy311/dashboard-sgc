-- CRM MÉDICO - SCHEMA ROBUSTO (PostgreSQL)
-- Diseñado para integración con Supabase Auth & RLS

-- 1. EXTENSIONES Y ENUMS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'doctor', 'nurse', 'staff');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE appointment_status AS ENUM ('scheduled', 'confirmed', 'cancelled', 'completed', 'no_show');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. FUNCIÓN PARA UPDATED_AT
CREATE OR REPLACE FUNCTION handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. TABLAS

-- Profiles (Vínculo con auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    role user_role DEFAULT 'staff',
    specialty TEXT,
    phone TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insurers (Aseguradoras)
CREATE TABLE IF NOT EXISTS public.insurers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    agreement_details TEXT,
    contact_info TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Patients (Pacientes)
CREATE TABLE IF NOT EXISTS public.patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name TEXT NOT NULL,
    id_number TEXT UNIQUE, -- DNI/Cédula
    birth_date DATE NOT NULL,
    gender TEXT,
    email TEXT UNIQUE,
    phone TEXT,
    address TEXT,
    emergency_contact TEXT,
    medical_history JSONB DEFAULT '{}',
    insurer_id UUID REFERENCES public.insurers(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Appointments (Citas)
CREATE TABLE IF NOT EXISTS public.appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES public.profiles(id),
    appointment_date TIMESTAMPTZ NOT NULL,
    status appointment_status DEFAULT 'scheduled',
    reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Medical Records (Historias Clínicas)
CREATE TABLE IF NOT EXISTS public.medical_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES public.profiles(id),
    appointment_id UUID REFERENCES public.appointments(id),
    evolution_notes TEXT NOT NULL,
    diagnosis TEXT NOT NULL,
    physical_exam TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Inventory (Farmacia/Insumos)
CREATE TABLE IF NOT EXISTS public.inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_name TEXT NOT NULL,
    sku TEXT UNIQUE,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    batch_number TEXT,
    expiry_date DATE,
    unit_price DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Prescriptions (Recetas)
CREATE TABLE IF NOT EXISTS public.prescriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES public.profiles(id),
    appointment_id UUID REFERENCES public.appointments(id),
    medicines JSONB NOT NULL, -- Ejemplo: [{"name": "Paracetamol", "dose": "500mg", "freq": "cada 8h"}]
    indications TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Lab Results (Resultados de Laboratorio)
CREATE TABLE IF NOT EXISTS public.lab_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    doctor_id UUID REFERENCES public.profiles(id),
    title TEXT NOT NULL,
    file_url TEXT NOT NULL,
    description TEXT,
    result_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. TRIGGERS PARA UPDATED_AT
CREATE TRIGGER tr_profiles_update BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE PROCEDURE handle_updated_at();
CREATE TRIGGER tr_insurers_update BEFORE UPDATE ON insurers FOR EACH ROW EXECUTE PROCEDURE handle_updated_at();
CREATE TRIGGER tr_patients_update BEFORE UPDATE ON patients FOR EACH ROW EXECUTE PROCEDURE handle_updated_at();
CREATE TRIGGER tr_appointments_update BEFORE UPDATE ON appointments FOR EACH ROW EXECUTE PROCEDURE handle_updated_at();
CREATE TRIGGER tr_medical_records_update BEFORE UPDATE ON medical_records FOR EACH ROW EXECUTE PROCEDURE handle_updated_at();
CREATE TRIGGER tr_inventory_update BEFORE UPDATE ON inventory FOR EACH ROW EXECUTE PROCEDURE handle_updated_at();
CREATE TRIGGER tr_prescriptions_update BEFORE UPDATE ON prescriptions FOR EACH ROW EXECUTE PROCEDURE handle_updated_at();
CREATE TRIGGER tr_lab_results_update BEFORE UPDATE ON lab_results FOR EACH ROW EXECUTE PROCEDURE handle_updated_at();

-- 5. ROW LEVEL SECURITY (RLS)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.medical_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prescriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lab_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insurers ENABLE ROW LEVEL SECURITY;

-- POLÍTICAS BÁSICAS (Ejemplos)

-- Perfiles: Todos los autenticados pueden ver perfiles, solo el dueño puede editar el suyo.
CREATE POLICY "Public profiles are viewable by everyone" ON profiles FOR SELECT USING (true);
CREATE POLICY "Users can edit their own profile" ON profiles FOR UPDATE USING (auth.uid() = id);

-- Pacientes: Solo staff médico puede ver/editar pacientes.
CREATE POLICY "Medical staff can manage patients" ON patients 
    FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin', 'doctor', 'nurse')));

-- Medical Records: Solo médicos y admin pueden ver/crear historias clínicas.
CREATE POLICY "Doctors and Admin can manage medical records" ON medical_records 
    FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin', 'doctor')));

-- Inventory: Todo el staff puede ver, solo admin y staff autorizado puede editar.
CREATE POLICY "Staff can view inventory" ON inventory FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Admin can manage inventory" ON inventory FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
