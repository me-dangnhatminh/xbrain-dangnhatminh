import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Plus, FolderOpen } from 'lucide-react';
import Header from '../components/layout/Header';

interface KnowledgeBase {
  id: string;
  name: string;
  createdAt: string;
  tenantId: string;
}

export default function KnowledgeBasesPage() {
  const navigate = useNavigate();
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newKbName, setNewKbName] = useState('');

  useEffect(() => {
    const currentTenant = localStorage.getItem('tenant_id');
    if (!currentTenant) {
      navigate('/');
      return;
    }
    setTenantId(currentTenant);

    const storedKbs = localStorage.getItem('mock_kbs');
    if (storedKbs) {
      setKbs(JSON.parse(storedKbs).filter((kb: KnowledgeBase) => kb.tenantId === currentTenant));
    }
  }, [navigate]);

  const handleCreateKb = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKbName.trim() || !tenantId) return;

    const newKb: KnowledgeBase = {
      id: `kb_${Date.now()}`,
      name: newKbName.trim(),
      createdAt: new Date().toLocaleDateString('en-GB'), // DD/MM/YYYY
      tenantId,
    };

    const allStoredKbs = JSON.parse(localStorage.getItem('mock_kbs') || '[]');
    const updatedAllKbs = [...allStoredKbs, newKb];
    
    localStorage.setItem('mock_kbs', JSON.stringify(updatedAllKbs));
    setKbs((prev) => [...prev, newKb]);
    
    setNewKbName('');
    setIsDialogOpen(false);
  };

  if (!tenantId) return null;

  const companyName = tenantId === 'company_a' ? 'Company A' : 'Company B';

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Header />
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 lg:p-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">Knowledge Bases</h1>
            <p className="text-slate-500 mt-1">
              Welcome, {companyName} — here are your document repositories.
            </p>
          </div>
          
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            {/* @ts-ignore */}
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                New Knowledge Base
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>Create Knowledge Base</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreateKb}>
                <div className="grid gap-4 py-4">
                  <div className="space-y-2">
                    <label htmlFor="name" className="text-sm font-medium">
                      Name
                    </label>
                    <Input
                      id="name"
                      placeholder="e.g. Contracts 2025"
                      value={newKbName}
                      onChange={(e: any) => setNewKbName(e.target.value)}
                      required
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button type="submit" disabled={!newKbName.trim()}>Create</Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {kbs.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-xl border border-dashed border-slate-300">
            <FolderOpen className="mx-auto h-12 w-12 text-slate-300" />
            <h3 className="mt-4 text-lg font-semibold text-slate-900">No Knowledge Bases</h3>
            <p className="mt-2 text-sm text-slate-500 max-w-sm mx-auto">
              You haven't created any document repositories yet. Create your first knowledge base to get started.
            </p>
            <Button onClick={() => setIsDialogOpen(true)} className="mt-6" variant="outline">
              <Plus className="mr-2 h-4 w-4" /> Create One Now
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {kbs.map((kb) => (
              <Card key={kb.id} className="flex flex-col hover:shadow-md transition-shadow">
                <CardHeader>
                  <CardTitle className="text-xl line-clamp-1" title={kb.name}>{kb.name}</CardTitle>
                </CardHeader>
                <CardContent className="flex-1">
                  <p className="text-sm text-slate-500">
                    Created on {kb.createdAt}
                  </p>
                </CardContent>
                <CardFooter>
                  <Button 
                    className="w-full" 
                    variant="secondary"
                    onClick={() => navigate(`/kb?kb_id=${kb.id}`)}
                  >
                    Open Workspace
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
