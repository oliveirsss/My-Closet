import { useState } from 'react';
import { UserType } from '../../types';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Search, User, ArrowRight, Sparkles } from 'lucide-react';
import { supabase } from '../../lib/supabase';
import * as api from '../../services/api';
import { motion, AnimatePresence } from 'framer-motion';

import { toast } from 'sonner';

interface LoginScreenProps {
  onLogin: (type: UserType, email?: string, password?: string) => void;
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isSignup, setIsSignup] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<string>('client');

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
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (error) throw error;

        // CORREÇÃO: Não chamamos onLogin com password para evitar duplo login no App.tsx se não for necessário,
        // mas o App.tsx espera email/pass para fazer login se fornecidos.
        // No entanto, aqui JÁ fizemos login. O ideal seria o App.tsx verificar sessão.
        // Mas para não partir a lógica existente, mantemos como está mas garantimos que o erro é apanhado AQUI.
        onLogin('client', email, password);
      }
    } catch (error: any) {
      console.error('Auth error:', error);
      toast.error("Email ou password inválidos!");
    } finally {
      setLoading(false);
    }
  };

  const handleVisitorAccess = () => {
    onLogin('visitor');
  };

  return (
    <div className="min-h-screen w-full relative bg-slate-50 flex flex-col items-center justify-center py-12 px-4 overflow-x-hidden">
      {/* Background with animated gradient */}
      <div
        className="fixed inset-0 z-0 opacity-30"
        style={{
          background: 'linear-gradient(135deg, #ecfdf5 0%, #f5f5f4 50%, #e0f2fe 100%)',
          backgroundSize: '400% 400%',
          animation: 'gradientBG 15s ease infinite'
        }}
      />

      {/* Decorative elements */}
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 0.05, scale: 1 }}
        transition={{ duration: 2, repeat: Infinity, repeatType: "reverse" }}
        className="fixed top-20 left-20 w-64 h-64 rounded-full bg-emerald-400 blur-3xl z-0"
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 0.05, scale: 1 }}
        transition={{ duration: 2.5, repeat: Infinity, repeatType: "reverse", delay: 1 }}
        className="fixed bottom-20 right-20 w-80 h-80 rounded-full bg-blue-400 blur-3xl z-0"
      />

      <div className="w-full max-w-5xl relative z-10">
        <motion.div
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center justify-center p-3 mb-6 bg-white/50 backdrop-blur-sm rounded-full shadow-sm">
            <Sparkles className="h-6 w-6 text-emerald-600 mr-2" />
            <h1 className="text-5xl font-light text-slate-800 tracking-tight">My Closet</h1>
          </div>
          <p className="text-xl text-slate-500 font-light tracking-wide">Gestão Inteligente de Inventário Têxtil</p>
        </motion.div>

        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="w-full max-w-4xl mx-auto"
        >
          <TabsList className="grid w-full grid-cols-2 mb-12 h-16 bg-white/40 backdrop-blur-md border border-white/50 p-1.5 rounded-2xl shadow-lg">
            <TabsTrigger
              value="client"
              className="rounded-xl text-md font-medium data-[state=active]:bg-white data-[state=active]:text-emerald-800 data-[state=active]:shadow-md transition-all duration-300"
            >
              <User className="mr-2 h-5 w-5" />
              <span className="flex flex-col items-start text-left">
                <span className="leading-none">Cliente</span>
                <span className="text-xs opacity-70 font-normal mt-0.5">Utilizador Pessoal</span>
              </span>
            </TabsTrigger>
            <TabsTrigger
              value="visitor"
              className="rounded-xl text-md font-medium data-[state=active]:bg-white data-[state=active]:text-blue-800 data-[state=active]:shadow-md transition-all duration-300"
            >
              <Search className="mr-2 h-5 w-5" />
              <span className="flex flex-col items-start text-left">
                <span className="leading-none">Investigador</span>
                <span className="text-xs opacity-70 font-normal mt-0.5">Visitante Público</span>
              </span>
            </TabsTrigger>
          </TabsList>

          <div className="relative min-h-[400px]">
            <AnimatePresence mode="wait">
              {activeTab === 'client' ? (
                <TabsContent value="client" key="client" asChild forceMount>
                  <motion.div
                    initial={{ x: -20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: 20, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                    className="absolute inset-x-0 top-0"
                  >
                    <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl p-8 max-w-md mx-auto border border-white/60 ring-1 ring-emerald-100">
                      <div className="mb-8 text-center">
                        <h2 className="text-2xl font-semibold mb-2 text-emerald-950">
                          {isSignup ? 'Começar Jornada' : 'Bem-vindo de volta'}
                        </h2>
                        <p className="text-slate-500 text-sm">
                          {isSignup
                            ? 'Crie a sua conta para digitalizar o seu guarda-roupa'
                            : 'Entre para gerir o seu inventário pessoal'}
                        </p>
                      </div>

                      <form onSubmit={handleClientLogin} className="space-y-5">
                        <AnimatePresence mode="popLayout">
                          {isSignup && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="overflow-hidden"
                            >
                              <div className="mb-5">
                                <Label htmlFor="name">Nome</Label>
                                <Input
                                  id="name"
                                  type="text"
                                  placeholder="Como devemos chamar-lhe?"
                                  value={name}
                                  onChange={(e) => setName(e.target.value)}
                                  required
                                  className="mt-1.5 bg-white/50 border-slate-200 focus:border-emerald-500 focus:ring-emerald-500/20"
                                />
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>

                        <div>
                          <Label htmlFor="email">Email</Label>
                          <Input
                            id="email"
                            type="email"
                            placeholder="seu@email.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            className="mt-1.5 bg-white/50 border-slate-200 focus:border-emerald-500 focus:ring-emerald-500/20"
                          />
                        </div>

                        <div>
                          <Label htmlFor="password">Palavra-passe</Label>
                          <Input
                            id="password"
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            className="mt-1.5 bg-white/50 border-slate-200 focus:border-emerald-500 focus:ring-emerald-500/20"
                          />
                        </div>

                        <Button
                          type="submit"
                          className="w-full bg-emerald-700 hover:bg-emerald-800 text-white h-11 text-md shadow-lg shadow-emerald-700/20 transition-all hover:scale-[1.02]"
                          disabled={loading}
                        >
                          {loading ? (
                            <div className="flex items-center">
                              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2"></span>
                              Processando...
                            </div>
                          ) : (
                            <span className="flex items-center">
                              {isSignup ? 'Criar Conta' : 'Entrar'}
                              <ArrowRight className="ml-2 h-4 w-4" />
                            </span>
                          )}
                        </Button>

                        <div className="text-center pt-2">
                          <p className="text-sm text-slate-500">
                            {isSignup ? 'Já tem conta?' : 'Ainda não tem conta?'}{' '}
                            <button
                              type="button"
                              onClick={() => setIsSignup(!isSignup)}
                              className="text-emerald-700 font-medium hover:text-emerald-800 hover:underline transition-colors"
                            >
                              {isSignup ? 'Entrar' : 'Criar conta'}
                            </button>
                          </p>
                        </div>
                      </form>
                    </div>
                  </motion.div>
                </TabsContent>
              ) : (
                <TabsContent value="visitor" key="visitor" asChild forceMount>
                  <motion.div
                    initial={{ x: 20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: -20, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                    className="absolute inset-x-0 top-0"
                  >
                    <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl p-8 max-w-md mx-auto border border-white/60 ring-1 ring-blue-100">
                      <div className="mb-6 text-center">
                        <h2 className="text-2xl font-semibold mb-2 text-slate-800">Acesso de Investigação</h2>
                        <p className="text-slate-500 text-sm">
                          Portal público para análise de dados e tendências têxteis
                        </p>
                      </div>

                      <div className="space-y-6">
                        <div className="bg-slate-50/80 rounded-2xl p-5 border border-slate-100">
                          <h3 className="mb-3 font-medium text-slate-700 flex items-center">
                            <Sparkles className="w-4 h-4 text-amber-500 mr-2" />
                            Dados Disponíveis
                          </h3>
                          <ul className="text-sm text-slate-600 space-y-2.5">
                            <li className="flex items-start">
                              <span className="mr-2 text-slate-400">•</span>
                              Tendências globais de materiais
                            </li>
                            <li className="flex items-start">
                              <span className="mr-2 text-slate-400">•</span>
                              Estatísticas de uso por camada
                            </li>
                            <li className="flex items-start">
                              <span className="mr-2 text-slate-400">•</span>
                              Correlação temperatura vs. vestuário
                            </li>
                            <li className="flex items-start">
                              <span className="mr-2 text-slate-400">•</span>
                              Dados anonimizados de inventários
                            </li>
                          </ul>
                        </div>

                        <Button
                          onClick={handleVisitorAccess}
                          className="w-full bg-slate-800 hover:bg-slate-900 text-white h-11 text-md shadow-lg shadow-slate-800/20 transition-all hover:scale-[1.02]"
                        >
                          <span className="flex items-center">
                            Aceder como Visitante
                            <ArrowRight className="ml-2 h-4 w-4" />
                          </span>
                        </Button>
                      </div>
                    </div>
                  </motion.div>
                </TabsContent>
              )}
            </AnimatePresence>
          </div>
        </Tabs>
      </div>

      <style>{`
        @keyframes gradientBG {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
      `}</style>
    </div>
  );
}