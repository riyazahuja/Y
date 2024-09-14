import React from "react";
import { TweetProps } from "./Tweet";

export function Body(props: TweetProps) {
  return (
    <>
      <p className="text-tweet whitespace-pre-line break-words">{props.body}</p>
      {props.images[0] && (
        <div className="my-3 mr-2 flex rounded-2xl ">
          <img className="rounded-2xl" src={props.images[0]} alt="" />
        </div>
      )}
    </>
  );
}
