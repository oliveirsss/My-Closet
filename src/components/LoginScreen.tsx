import { useState } from 'react';
import { UserType } from '../App';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Search, User } from 'lucide-react';
import { supabase } from '../utils/supabase-client';
import * as api from '../utils/api';

interface LoginScreenProps {
  onLogin: (type: UserType, email?: string, password?: string) => void;
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isSignup, setIsSignup] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleClientLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      if (isSignup) {
        // Sign up
        const { user } = await api.signup(email, password, name);
        
        // After signup, sign in
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (error) throw error;

        if (data.session?.access_token) {
          onLogin('client', email, password);
        }
      } else {
        // Sign in
        onLogin('client', email, password);
      }
    } catch (error: any) {
      console.error('Auth error:', error);
      alert(error.message || 'Erro ao autenticar');
    } finally {
      setLoading(false);
    }
  };

  const handleVisitorAccess = () => {
    onLogin('visitor');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-stone-100 p-4">
      <div 
        className="absolute inset-0 opacity-5"
        style={{
          backgroundImage: 'url("https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=1200")',
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }}
      />
      
      <div className="w-full max-w-5xl relative z-10">
        <div className="text-center mb-12">
          <h1 className="text-6xl mb-4 text-emerald-900">My Closet</h1>
          <p className="text-xl text-stone-600">Gestão Inteligente de Inventário Têxtil</p>
        </div>

        <Tabs defaultValue="client" className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-8 h-14">
            <TabsTrigger value="client" className="text-lg">
              <User className="mr-2 h-5 w-5" />
              Cliente / Utilizador Pessoal
            </TabsTrigger>
            <TabsTrigger value="visitor" className="text-lg">
              <Search className="mr-2 h-5 w-5" />
              Investigador / Visitante
            </TabsTrigger>
          </TabsList>

          <TabsContent value="client">
            <div className="bg-white/80 backdrop-blur rounded-lg shadow-xl p-8 max-w-md mx-auto border border-stone-200">
              <div className="mb-6">
                <h2 className="text-2xl mb-2 text-emerald-900">
                  {isSignup ? 'Criar Conta' : 'Acesso Pessoal'}
                </h2>
                <p className="text-stone-600">
                  {isSignup 
                    ? 'Crie a sua conta para começar a gerir o seu guarda-roupa' 
                    : 'Entre para gerir o seu guarda-roupa privado'}
                </p>
              </div>

              <form onSubmit={handleClientLogin} className="space-y-4">
                {isSignup && (
                  <div>
                    <Label htmlFor="name">Nome</Label>
                    <Input
                      id="name"
                      type="text"
                      placeholder="Seu nome"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      className="mt-1"
                    />
                  </div>
                )}

                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="seu@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="mt-1"
                  />
                </div>

                <div>
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="mt-1"
                  />
                </div>

                <Button 
                  type="submit" 
                  className="w-full bg-emerald-700 hover:bg-emerald-800"
                  disabled={loading}
                >
                  {loading ? 'A processar...' : (isSignup ? 'Criar Conta' : 'Entrar')}
                </Button>

                <p className="text-sm text-center text-stone-500">
                  {isSignup ? 'Já tem conta?' : 'Não tem conta?'}{' '}
                  <button
                    type="button"
                    onClick={() => setIsSignup(!isSignup)}
                    className="text-emerald-700 hover:underline"
                  >
                    {isSignup ? 'Entrar' : 'Criar conta'}
                  </button>
                </p>
              </form>
            </div>
          </TabsContent>

          <TabsContent value="visitor">
            <div className="bg-white/80 backdrop-blur rounded-lg shadow-xl p-8 max-w-md mx-auto border border-stone-200">
              <div className="mb-6">
                <h2 className="text-2xl mb-2 text-emerald-900">Acesso de Investigação</h2>
                <p className="text-stone-600">
                  Explore a base de dados pública para análise estatística e tendências de materiais
                </p>
              </div>

              <div className="space-y-4">
                <div className="bg-stone-50 rounded-lg p-4 border border-stone-200">
                  <h3 className="mb-2 text-emerald-900">Dados Disponíveis:</h3>
                  <ul className="text-sm text-stone-600 space-y-1">
                    <li>• Tendências de materiais têxteis</li>
                    <li>• Estatísticas de uso por camada</li>
                    <li>• Análise de temperatura vs roupa</li>
                    <li>• Dados anonimizados de inventários</li>
                  </ul>
                </div>

                <Button 
                  onClick={handleVisitorAccess}
                  className="w-full bg-stone-700 hover:bg-stone-800"
                >
                  Aceder como Visitante
                </Button>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}