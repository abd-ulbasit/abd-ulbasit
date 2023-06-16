'use client'
import type { IconType } from "react-icons"
import { FaEnvelope, FaGithub, FaLinkedin, FaTwitter } from "react-icons/fa"
function Socials() {
  //make an array socials that has opjects with two properties one is src one is icon that is of IconType
  interface social { src: string, icon: IconType }
  const socials: social[] = [{ src: "www.github.com/abd-ulbasit", icon: FaGithub }, { src: "www.linkedin.com/in/abd-ulbasit", icon: FaLinkedin }, { src: "www.twitter.com/abd_lbasit", icon: FaTwitter },
    // { src: "mailto:basit01035@gmail.com", icon: FaEnvelope }
  ]
  return <span
    className="inline-flex -space-x-px overflow-hidden rounded-md border bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900"
  >{socials.map((social) => {

    return <button key={social.src} onClick={(e) => { e.preventDefault(); window.open(`https://${social.src}`, "_blank") }}
      className="inline-block px-8 py-2  font-medium text-gray-700 hover:bg-gray-50 focus:relative dark:text-gray-200 dark:hover:bg-gray-800"
    >
      {<social.icon></social.icon>}
    </button>
  })

    }

  </span>

}
export default Socials;