"use client";

import { useEffect } from "react";
import { useGameStore } from "@/stores/gameStore";
import { Settings, Wifi, Volume2, Mic } from "lucide-react";

const PROVIDERS = [
  { value: "offline", label: "离线策略（无需API）" },
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "qwen", label: "通义千问" },
  { value: "ollama", label: "Ollama（本地）" },
];

export default function SettingsPage() {
  const { aiConfig, setAiConfig, testConnection, loading, status } =
    useGameStore();

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-8">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <Settings size={24} className="text-amber-400" />
        全局设置
      </h1>

      {/* AI 模型配置 */}
      <section className="bg-gray-900 rounded-xl p-6 space-y-4 border border-gray-800">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Wifi size={18} className="text-amber-400" />
          AI 模型配置
        </h2>

        <div className="grid gap-4">
          <label className="block">
            <span className="text-sm text-gray-400">Provider</span>
            <select
              value={aiConfig.provider}
              onChange={(e) => setAiConfig({ provider: e.target.value })}
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:ring-amber-500 focus:border-amber-500"
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-sm text-gray-400">Model</span>
            <input
              type="text"
              value={aiConfig.model}
              onChange={(e) => setAiConfig({ model: e.target.value })}
              placeholder="gpt-4o-mini"
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:ring-amber-500 focus:border-amber-500"
            />
          </label>

          <label className="block">
            <span className="text-sm text-gray-400">API Key</span>
            <input
              type="password"
              value={aiConfig.api_key}
              onChange={(e) => setAiConfig({ api_key: e.target.value })}
              placeholder="sk-..."
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:ring-amber-500 focus:border-amber-500"
            />
          </label>

          <label className="block">
            <span className="text-sm text-gray-400">Base URL</span>
            <input
              type="text"
              value={aiConfig.base_url}
              onChange={(e) => setAiConfig({ base_url: e.target.value })}
              placeholder="https://api.openai.com/v1"
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:ring-amber-500 focus:border-amber-500"
            />
          </label>

          <div className="grid grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm text-gray-400">Temperature</span>
              <input
                type="number"
                min={0}
                max={2}
                step={0.05}
                value={aiConfig.temperature}
                onChange={(e) =>
                  setAiConfig({ temperature: Number(e.target.value) })
                }
                className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
              />
            </label>
            <label className="block">
              <span className="text-sm text-gray-400">Timeout (秒)</span>
              <input
                type="number"
                min={3}
                max={120}
                value={aiConfig.timeout_seconds}
                onChange={(e) =>
                  setAiConfig({ timeout_seconds: Number(e.target.value) })
                }
                className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
              />
            </label>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={testConnection}
            disabled={loading}
            className="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-sm font-medium rounded-lg transition-colors"
          >
            {loading ? "测试中..." : "测试连接"}
          </button>
          {status && (
            <span className="text-sm text-gray-400">{status}</span>
          )}
        </div>
      </section>

      {/* TTS 配置 */}
      <section className="bg-gray-900 rounded-xl p-6 space-y-4 border border-gray-800">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Volume2 size={18} className="text-amber-400" />
          语音合成 (TTS)
        </h2>
        <p className="text-sm text-gray-500">
          TTS 功能将在后续版本中开放，敬请期待。
        </p>
      </section>

      {/* STT 配置 */}
      <section className="bg-gray-900 rounded-xl p-6 space-y-4 border border-gray-800">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Mic size={18} className="text-amber-400" />
          语音识别 (STT)
        </h2>
        <p className="text-sm text-gray-500">
          语音识别功能将在后续版本中开放，敬请期待。
        </p>
      </section>
    </div>
  );
}
