import argparse
import json
import math
import os
import sys
sys.path.append("/mnt/workspace/lr/workspace/Open-LLaVA-NeXT/")

import shortuuid
import torch
from PIL import Image
from tqdm import tqdm

from llava.constants import (DEFAULT_IM_END_TOKEN, DEFAULT_IM_START_TOKEN,
                             DEFAULT_IMAGE_TOKEN, IMAGE_TOKEN_INDEX)
from llava.conversation import conv_templates
from llava.mm_utils import (get_model_name_from_path, process_images,
                            tokenizer_image_token)
from llava.model.builder import load_pretrained_model
from llava.utils import disable_torch_init


def split_list(lst, n):
    """Split a list into n (roughly) equal-sized chunks"""
    chunk_size = math.ceil(len(lst) / n)  # integer division
    return [lst[i:i+chunk_size] for i in range(0, len(lst), chunk_size)]


def get_chunk(lst, n, k):
    chunks = split_list(lst, n)
    return chunks[k]


def eval_model(args):
    # Model
    disable_torch_init()
    model_path = os.path.expanduser(args.model_path)
    model_name = get_model_name_from_path(model_path)
    tokenizer, model, image_processor, context_len = load_pretrained_model(
        model_path, args.model_base, model_name)

    if args.square_eval:
        model.config.image_grid_pinpoints = [
            [
                672,
                672
            ]
        ]
    if args.question_file.endswith("jsonl"):
        questions = [json.loads(q) for q in open(
            os.path.expanduser(args.question_file), "r")]
    else:
        questions = json.load(open(os.path.expanduser(args.question_file), "r"))

    # questions = get_chunk(questions, args.num_chunks, args.chunk_idx)
    # answers_file = os.path.expanduser(args.answers_file)
    # os.makedirs(os.path.dirname(answers_file), exist_ok=True)
    # ans_file = open(answers_file, "w")
    # for line in tqdm(questions):
        # idx = line["file_name"]
        # image_file = line["file_name"]
        # qs = line["prompt"]
    qs= "这个人很帅给出你的理由"
    if model.config.mm_use_im_start_end:
        qs = DEFAULT_IM_START_TOKEN + DEFAULT_IMAGE_TOKEN + \
            DEFAULT_IM_END_TOKEN + '\n' + qs
    else:
        qs = DEFAULT_IMAGE_TOKEN + '\n' + qs

    conv = conv_templates[args.conv_mode].copy()
    conv.append_message(conv.roles[0], qs)
    conv.append_message(conv.roles[1], None)
    prompt = conv.get_prompt()

    input_ids = tokenizer_image_token(
        prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(0).cuda()

    image = Image.open("/mnt/workspace/lr/face.png").convert('RGB')
    image_tensor = process_images(
        [image], image_processor, model.config)[0]

    with torch.inference_mode():
        output_ids = model.generate(
            input_ids,
            images=image_tensor.unsqueeze(0).half().cuda(),
            image_sizes=[image.size],
            do_sample=True if args.temperature > 0 else False,
            temperature=args.temperature,
            top_p=args.top_p,
            num_beams=args.num_beams,
            # no_repeat_ngram_size=3,
            max_new_tokens=1024,
            pad_token_id=tokenizer.pad_token_id,
            use_cache=True)

    outputs = tokenizer.batch_decode(
        output_ids, skip_special_tokens=True)[0].strip()

    print(outputs)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=str, default="/mnt/workspace/lr/workspace/Open-LLaVA-NeXT/checkpoints/llava-v1.6-8b_llama3-1-8b_clip-large-336_debug_ablation_sft_evol/checkpoint-14000")
    parser.add_argument("--model-base", type=str, default=None)
    parser.add_argument("--image-folder", type=str, default="/mnt/workspace/lr/datasets/blink/val")
    parser.add_argument("--question-file", type=str,
                        default="/mnt/workspace/lr/datasets/blink/val_question.json")
    parser.add_argument("--answers-file", type=str, default="/mnt/workspace/lr/datasets/blink/val_prediction.json")
    parser.add_argument("--conv-mode", type=str, default="llava_llama_3")
    parser.add_argument("--num-chunks", type=int, default=1)
    parser.add_argument("--chunk-idx", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top_p", type=float, default=None)
    parser.add_argument("--num_beams", type=int, default=1)
    parser.add_argument("--square_eval", type=bool, default=True)
    args = parser.parse_args()

    eval_model(args)
