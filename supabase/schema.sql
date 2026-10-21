-- Leaderboard table for the TASI 2020 simulator (run once in the Supabase SQL editor)
create table if not exists public.leaderboard (
  id bigint generated always as identity primary key,
  player text not null check (char_length(player) between 1 and 40),
  final_value numeric not null,
  pnl numeric not null,
  benchmark_pnl numeric not null,
  alpha numeric not null,
  created_at timestamptz not null default now()
);

alter table public.leaderboard enable row level security;

-- Anyone can read the board and submit a score; nobody can edit or delete through the public key
create policy "leaderboard read" on public.leaderboard for select using (true);
create policy "leaderboard insert" on public.leaderboard for insert with check (true);
