#!/bin/bash
# Fine-tuning script for FF_Agent

echo "🚀 Starting Fine-tuning Process"
echo "================================"

# For OpenAI GPT
# openai api fine_tunes.create \
#   -t finetuning_data/train_openai.jsonl \
#   -v finetuning_data/validation_openai.jsonl \
#   --model gpt-3.5-turbo \
#   --n_epochs 3

# For Google Gemini (using Vertex AI)
# gcloud ai custom-jobs create \
#   --region=us-central1 \
#   --display-name="ff-agent-finetuning" \
#   --config=training_config.yaml

echo "✅ Fine-tuning job submitted"
echo "Monitor progress in your cloud console"
