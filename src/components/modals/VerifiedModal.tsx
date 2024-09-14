import { Dialog, Transition } from "@headlessui/react";
import { signIn } from "next-auth/react";
import { Fragment } from "react";

import { useForm, SubmitHandler } from "react-hook-form";
import { TweetInput } from "@components/inputs/TweetInput";
import VerifiedDropdown from "./VerifiedDropdown";
import MainButton from "@components/MainButton";

type Inputs = {
    username: string;
    password: string;
};
export default function VerifiedModal({
    isOpen,
    closeModal,
}: {
    isOpen: boolean;
    closeModal: any;
}) {
    const {
        register,
        handleSubmit,
        watch,
        reset,
        formState: { errors },
    } = useForm<Inputs>();

    const onSubmit: SubmitHandler<Inputs> = (data) => {
        console.log("cred data", data);
        signIn("credentials", { ...data });
        reset();
    };
    return (
        <>
            <Transition appear show={isOpen} as={Fragment}>
                <Dialog as="div" className="relative z-10" onClose={closeModal}>
                    <Transition.Child
                        as={Fragment}
                        enter="ease-out duration-300"
                        enterFrom="opacity-0"
                        enterTo="opacity-100"
                        leave="ease-in duration-200"
                        leaveFrom="opacity-100"
                        leaveTo="opacity-0"
                    >
                        <div className="fixed inset-0 bg-black bg-opacity-25" />
                    </Transition.Child>

                    <div className="fixed inset-0 overflow-y-auto">
                        <div className="flex min-h-full items-center justify-center p-4 text-center">
                            <Transition.Child
                                as={Fragment}
                                enter="ease-out duration-300"
                                enterFrom="opacity-0 scale-95"
                                enterTo="opacity-100 scale-100"
                                leave="ease-in duration-200"
                                leaveFrom="opacity-100 scale-100"
                                leaveTo="opacity-0 scale-95"
                            >
                                <Dialog.Panel className="flex w-[100%] max-w-xl transform flex-col content-center items-center  gap-4 overflow-hidden rounded-2xl bg-white p-2 text-left align-middle text-white shadow-xl transition-all dark:bg-black dark:text-white md:p-6">
                                    <Dialog.Title
                                        className="text-3xl font-semibold leading-6 py-2  text-black dark:text-white "
                                    >
                                        Choose your badge
                                    </Dialog.Title>
                                        <div className="flex items-center gap-2">
                                    <VerifiedDropdown closeModal={closeModal}/>
                                    </div>
                                </Dialog.Panel>
                            </Transition.Child>
                        </div>
                    </div>
                </Dialog>
            </Transition>
        </>
    );
}
