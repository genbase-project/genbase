// src/settings/ModelSettings.tsx
import React, { useState, useEffect } from 'react';
import { useToast } from '@/hooks/use-toast';
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
// Using Card which should adapt to theme
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

const ModelSettings: React.FC = () => {
    const { toast } = useToast();
    const [availableModels, setAvailableModels] = useState<Record<string, any[]>>({});
    const [currentModel, setCurrentModel] = useState<string>('');
    const [selectedProvider, setSelectedProvider] = useState<string>('');
    const [selectedModel, setSelectedModel] = useState<string>('');
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        const fetchModels = async () => {
            setIsLoading(true);
            try {
                const [availableRes, currentRes] = await Promise.all([
                    fetchWithAuth(`${ENGINE_BASE_URL}/model/list`),
                    fetchWithAuth(`${ENGINE_BASE_URL}/model/current`)
                ]);

                let fetchedCurrentModel = '';
                if (currentRes.ok) {
                    const current = await currentRes.json();
                    fetchedCurrentModel = current.model_name;
                    setCurrentModel(fetchedCurrentModel);
                    setSelectedModel(fetchedCurrentModel);
                } else {
                    console.error("Failed to fetch current model:", currentRes.statusText);
                }

                if (availableRes.ok) {
                    const models = await availableRes.json();
                    setAvailableModels(models);
                    if (fetchedCurrentModel && models) {
                         const provider = Object.keys(models).find(p =>
                            models[p]?.some((model: any) => model.name === fetchedCurrentModel)
                         );
                         if(provider) {
                            setSelectedProvider(provider);
                         }
                    }
                } else {
                    console.error("Failed to fetch available models:", availableRes.statusText);
                    toast({ title: "Error", description: "Failed to fetch available models", variant: "destructive" });
                }
            } catch (error) {
                console.error('Error fetching model data:', error);
                toast({ title: "Error", description: "Failed to fetch model data", variant: "destructive" });
            } finally {
                setIsLoading(false);
            }
        };
        fetchModels();
    }, [toast]);


    const handleSaveModelSettings = async () => {
        if (!selectedModel || selectedModel === currentModel) return;
        setIsSaving(true);
        try {
            const res = await fetchWithAuth(`${ENGINE_BASE_URL}/model/set`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: selectedModel })
            });

            if (res.ok) {
                setCurrentModel(selectedModel);
                toast({ title: "Success", description: "Model settings saved successfully", variant: "default" });
            } else {
                const errorData = await res.json().catch(() => ({ message: 'Failed to update model' }));
                throw new Error(errorData.detail || errorData.message || 'Failed to update model');
            }
        } catch (error: any) {
            console.error('Error saving model settings:', error);
            toast({ title: "Error", description: error.message || "Failed to save model settings", variant: "destructive" });
        } finally {
            setIsSaving(false);
        }
    };

    const handleProviderChange = (value: string) => {
        setSelectedProvider(value);
        const modelsInNewProvider = availableModels[value] || [];
        if (!modelsInNewProvider.some(m => m.name === selectedModel)) {
             setSelectedModel('');
        }
    }

    const isSaveDisabled = !selectedModel || selectedModel === currentModel || isSaving || isLoading;


    return (
        <div className="p-4 md:p-6 h-full overflow-y-auto bg-white text-neutral-900">
       
                <CardHeader>
                    <CardTitle className="text-xl">Language Model Configuration</CardTitle> 
                    <CardDescription> 
                        Select the AI model that will power your assistant's responses.
                        Current model: <span className="font-semibold">{currentModel || 'Not Set'}</span> 
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                     {isLoading ? (
                        <div className="space-y-4">
                            <div className="space-y-2"><Label>Provider</Label><Skeleton className="h-10 w-full rounded-md" /></div>
                            <div className="space-y-2"><Label>Model</Label><Skeleton className="h-10 w-full rounded-md" /></div>
                        </div>
                     ) : (
                        <>
                            <div className="space-y-2">
                                <Label htmlFor="provider" className="text-sm font-medium">Provider</Label> {/* Removed text-gray-300 */}
                                <Select
                                    onValueChange={handleProviderChange}
                                    value={selectedProvider}
                                    disabled={Object.keys(availableModels).length === 0}
                                >
                                    <SelectTrigger id="provider" className="focus:ring-ring disabled:opacity-50">
                                        <SelectValue placeholder="Select provider" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {Object.keys(availableModels).map((provider) => (
                                            <SelectItem key={provider} value={provider}> 
                                                <span className="capitalize">{provider}</span>
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="model" className="text-sm font-medium">Model</Label>
                                <Select
                                    value={selectedModel}
                                    onValueChange={setSelectedModel}
                                    disabled={!selectedProvider || !availableModels[selectedProvider]}
                                >
                                    <SelectTrigger id="model" className="focus:ring-ring disabled:opacity-50">
                                        <SelectValue placeholder="Select model" />
                                    </SelectTrigger>
                                    <SelectContent> {/* Removed bg/border */}
                                        {(availableModels[selectedProvider] || []).map((model) => (
                                            <SelectItem key={model.identifier || model.name} value={model.name}> 
                                                {model.label || model.name}
                                            </SelectItem>
                                        ))}
                                        {selectedProvider && !(availableModels[selectedProvider]?.length > 0) && (
                                            <div className="p-2 text-center text-sm text-muted-foreground">No models available for this provider.</div>
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>
                        </>
                     )}
                </CardContent>
                <CardFooter className="px-6 py-4 flex justify-end">
                    <Button
                        onClick={handleSaveModelSettings}
                        disabled={isSaveDisabled}
                        
                    >
                        {isSaving ? 'Saving...' : 'Save Changes'}
                    </Button>
                </CardFooter>
          
        </div>
    );
};

export default ModelSettings;